"""Offline tests of the harness itself: recording parsing, normalisation, seeds. No backend needed.

They guard the comparator in both directions: a recording compared with itself must be clean (the
normalisations do not invent differences), and each kind of real difference must be caught (the
normalisations do not hide them).
"""

from __future__ import annotations

import copy
import json
import os
import re

import pytest

from conformance.compare import Actual, Context, TimestampTracker, compare_response
from conformance.config import RECORDED_ORIGINS
from conformance.divergences import Divergence, load_divergences
from conformance.recordings import Expected, load_recording
from conformance.replay import apply_divergences, classify, load_manifest
from conformance.seeds import SCENARIO_NAMES, pinned_timestamps, sandbox_repo, scenario_seed

pytestmark = pytest.mark.offline
BACKEND = "http://127.0.0.1:8200"
RECORDINGS = [spec["recording"] for spec in load_manifest()["scenarios"].values()]


def ctx(pinned: set[str] | None = None) -> Context:
    return Context(TimestampTracker(pinned or set()), BACKEND, RECORDED_ORIGINS)


def _unredact(text: str) -> str:
    return re.sub(r"<email>|<HF_[A-Z_]*LOGIN>", "someone@example.com", text)


def actual_from_expected(expected: Expected) -> Actual:
    """What a perfect backend would send for this recorded step (as far as the recording knows)."""
    if expected.body_kind == "json":
        body = _unredact(json.dumps(expected.body, ensure_ascii=False, separators=(",", ":"))).encode()
    elif expected.body_kind in ("text", "text-prefix", "json-prefix"):
        body = _unredact(expected.body).encode()
    else:
        body = b""
    return Actual(expected.status, {k: _unredact(v) for k, v in expected.headers.items()}, body)


@pytest.mark.parametrize("file_name", RECORDINGS)
def test_recording_compared_with_itself_is_clean(file_name: str):
    recording = load_recording(file_name)
    context = ctx()
    for step in recording.steps:
        if step.expected.body_kind == "json-prefix":
            continue  # a cut JSON excerpt cannot stand for a whole body
        diffs = compare_response(step.expected, actual_from_expected(step.expected), context)
        assert diffs == [], (step.id, [d.as_dict() for d in diffs])


def test_recording_formats_and_counts():
    walkthrough = load_recording("2026-10-05-owner-walkthrough.json")
    assert walkthrough.format == "probe" and len(walkthrough.steps) == 98
    assert {s.persona for s in walkthrough.steps} == {"owner", "requester", "anonymous"}
    ui = load_recording("2026-10-05-ui-walkthrough.json")
    assert ui.format == "bridge-log" and len(ui.steps) == 62
    seed_reads = {s.id: s for s in load_recording("2026-10-05-clone-seed-reads.json").steps}
    assert seed_reads["whoami-bad-token"].persona == "bad"
    assert seed_reads["model-info-expand"].path == "/api/models/Orosius/deltanet-mla-latent?expand[]=gated&expand[]=cardData"


def test_body_kinds():
    reads = {s.id: s.expected for s in load_recording("2026-10-05-owner-reads.json").steps}
    assert reads["owner-report"].body_kind == "json"  # short excerpt parses: complete
    assert reads["owner-list-pending"].body_kind == "json-prefix"  # cut at 160 characters
    assert reads["owner-resolve"].body_kind == "text-prefix"
    seed_reads = {s.id: s.expected for s in load_recording("2026-10-05-clone-seed-reads.json").steps}
    assert seed_reads["owner-head-gitattributes"].body_kind == "empty"
    assert seed_reads["anon-ask-access-get"].body_kind == "unrecorded"  # HTML page
    assert seed_reads["owner-gitattributes"].body_kind == "text" and len(seed_reads["owner-gitattributes"].body) == 1519


def test_captured_headers_follow_each_recording():
    walkthrough = load_recording("2026-10-05-owner-walkthrough.json").steps[0].expected.captured
    assert "etag" not in walkthrough and "www-authenticate" in walkthrough
    anonymous = load_recording("2026-10-05-anonymous-probes.json").steps[0].expected.captured
    assert "content-disposition" not in anonymous  # probe.py did not keep it yet (git 7e14ba3)
    seed_reads = load_recording("2026-10-05-clone-seed-reads.json").steps[0].expected.captured
    assert {"etag", "www-authenticate", "x-repo-commit", "link"} <= seed_reads


# --- the comparator catches real differences ------------------------------------------------------

def _step(file_name: str, step_id: str):
    return next(s for s in load_recording(file_name).steps if s.id == step_id)


def _fields(expected: Expected, actual: Actual, context: Context | None = None) -> list[str]:
    return [d.field for d in compare_response(expected, actual, context or ctx())]


GATE_STEP = ("2026-10-05-owner-walkthrough.json", "s0-req-auth-check")


def test_status_and_error_headers_are_exact():
    expected = _step(*GATE_STEP).expected
    good = actual_from_expected(expected)
    assert _fields(expected, Actual(404, good.headers, good.body)) == ["status"]
    no_code = dict(good.headers)
    del no_code["x-error-code"]
    assert _fields(expected, Actual(403, no_code, good.body)) == ["header:x-error-code"]
    owner_error = _step("2026-10-05-owner-walkthrough.json", "s1-accept").expected
    with_code = {**actual_from_expected(owner_error).headers, "x-error-code": "NotFound"}
    assert _fields(owner_error, Actual(404, with_code, actual_from_expected(owner_error).body)) == ["header:x-error-code"]


def test_message_origin_is_not_normalised():
    expected = _step(*GATE_STEP).expected
    good = actual_from_expected(expected)
    message = expected.headers["x-error-message"].replace("https://huggingface.co", BACKEND)
    body = json.dumps({"error": message}).encode()
    assert _fields(expected, Actual(403, {**good.headers, "x-error-message": message}, body)) == [
        "header:x-error-message", "body$.error"]


def test_content_type_charset_counts():
    expected = _step(*GATE_STEP).expected
    good = actual_from_expected(expected)
    assert _fields(expected, Actual(403, {**good.headers, "content-type": "application/json"}, good.body)) == [
        "header:content-type"]
    assert _fields(expected, Actual(403, {**good.headers, "content-type": "application/json;charset=UTF-8"}, good.body)) == []


def test_location_origin_normalised_but_not_its_form():
    expected = _step("2026-10-05-owner-walkthrough.json", "s3-req-ask-again").expected
    good = actual_from_expected(expected)
    on_backend = {**good.headers, "location": f"{BACKEND}/Orosius/deltanet-mla-latent"}
    body = f"See Other. Redirecting to {BACKEND}/Orosius/deltanet-mla-latent".encode()
    assert _fields(expected, Actual(303, on_backend, body)) == []
    relative = {**good.headers, "location": "/Orosius/deltanet-mla-latent"}
    assert _fields(expected, Actual(303, relative, good.body)) == ["header:location"]


def test_json_key_order_values_and_emails():
    expected = _step("2026-10-05-owner-walkthrough.json", "s4-list-accepted").expected
    item = copy.deepcopy(expected.body[0])
    item["user"]["email"] = "someone@example.com"  # real address vs redacted recording: same
    good = Actual(200, {"content-type": "application/json; charset=utf-8"}, json.dumps([item]).encode())
    assert _fields(expected, good) == []
    reordered = {k: item[k] for k in ("user", "status", "timestamp", "reviewedAt", "grantedBy")}
    assert _fields(expected, Actual(200, good.headers, json.dumps([reordered]).encode())) == ["body$[0]:key-order"]
    no_email = copy.deepcopy(item)
    del no_email["user"]["email"]
    assert _fields(expected, Actual(200, good.headers, json.dumps([no_email]).encode())) == ["body$[0].user:keys"]
    extra = {**item, "rejectionReason": "x"}
    assert _fields(expected, Actual(200, good.headers, json.dumps([extra]).encode())) == ["body$[0]:keys"]
    as_int = copy.deepcopy(item)
    as_int["user"]["isPro"] = 0
    assert _fields(expected, Actual(200, good.headers, json.dumps([as_int]).encode())) == ["body$[0].user.isPro"]


def test_timestamps_keep_relations():
    recording = load_recording("2026-10-05-owner-walkthrough.json")
    steps = {s.id: s for s in recording.steps}
    pending = steps["s3b-list-pending"].expected  # timestamp T1
    accepted = steps["s4-list-accepted"].expected  # timestamp T1, reviewedAt T2 > T1

    def body(step_expected: Expected, mapping: dict[str, str]) -> Actual:
        text = json.dumps(step_expected.body)
        for old, new in mapping.items():
            text = text.replace(old, new)
        return Actual(200, {"content-type": "application/json; charset=utf-8"}, text.encode())

    t1, t2 = "2026-10-05T14:16:59.252Z", "2026-10-05T14:17:02.019Z"
    shifted = {t1: "2026-10-05T14:16:50.664Z", t2: "2026-10-05T14:16:51.664Z"}
    context = ctx()
    assert _fields(pending, body(pending, shifted), context) == []
    assert _fields(accepted, body(accepted, shifted), context) == []
    # timestamp must be kept on accept (TS-1): a different value is caught
    context = ctx()
    _fields(pending, body(pending, shifted), context)
    moved = {t1: "2026-10-05T14:16:52.664Z", t2: "2026-10-05T14:16:53.664Z"}
    assert "body$[0].timestamp" in _fields(accepted, body(accepted, moved), context)
    # order: reviewedAt before timestamp is caught
    context = ctx()
    swapped = {t1: "2026-10-05T14:16:51.664Z", t2: "2026-10-05T14:16:50.664Z"}
    assert _fields(accepted, body(accepted, swapped), context) == ["body$[0].reviewedAt"]
    # pinned (seeded) timestamps must come back verbatim
    context = ctx({t1})
    assert _fields(pending, body(pending, shifted), context) == ["body$[0].timestamp"]
    # HF's millisecond format
    context = ctx()
    assert _fields(pending, body(pending, {t1: "2026-10-05T14:16:50Z"}), context) == ["body$[0].timestamp"]


def test_etag_rules():
    file_step = _step("2026-10-05-clone-seed-reads.json", "owner-gitattributes").expected
    good = actual_from_expected(file_step)
    weak = {**good.headers, "etag": 'W/"a6344aac8c09253b3b630fb776ae94478aa0275b"'}
    assert _fields(file_step, Actual(200, weak, good.body)) == []
    other = {**good.headers, "etag": '"0000000000000000000000000000000000000000"'}
    assert _fields(file_step, Actual(200, other, good.body)) == ["header:etag"]
    json_step = _step("2026-10-05-clone-seed-reads.json", "whoami-anon").expected
    good = actual_from_expected(json_step)
    assert _fields(json_step, Actual(401, {**good.headers, "etag": 'W/"1-x"'}, good.body)) == []
    no_www = {k: v for k, v in good.headers.items() if k != "www-authenticate"}
    assert _fields(json_step, Actual(401, no_www, good.body)) == ["header:www-authenticate"]


def test_json_prefix_ignores_whitespace_not_order():
    expected = _step("2026-10-05-owner-reads.json", "owner-list-pending").expected
    full = [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c3753b1ba445d9b80ee712.svg",
                      "isPro": False, "fullname": "Bridge", "user": "TestingBOrig", "type": "user",
                      "verifiedOrgNames": [], "email": "t@example.com"},
             "timestamp": "2026-10-05T13:31:55.250Z", "status": "pending"}]
    headers = {"content-type": "application/json; charset=utf-8"}
    assert _fields(expected, Actual(200, headers, json.dumps(full, indent=2).encode())) == []
    full[0]["user"] = dict(reversed(list(full[0]["user"].items())))
    assert _fields(expected, Actual(200, headers, json.dumps(full).encode())) == ["body"]


def test_bridge_log_cut_strings_and_text():
    ui = {s.id: s.expected for s in load_recording("2026-10-05-ui-walkthrough.json").steps}
    resolve = ui["211"]
    assert resolve.body_kind == "text"  # .gitattributes is 1519 bytes, under the 2000 cut
    good = actual_from_expected(resolve)
    assert _fields(resolve, Actual(200, good.headers, good.body + b"extra")) == ["body"]


# --- seeds and divergences ------------------------------------------------------------------------

@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_scenario_seeds_build_and_serialise(name: str):
    document = scenario_seed(name)
    json.dumps(document)
    assert {"seed", "now", "tick_ms", "users", "repos", "requests"} <= set(document)
    tokens = {u["token"] for u in document["users"]}
    assert {"persona-owner", "persona-requester"} <= tokens


def test_sandbox_repo_matches_recording():
    repo = sandbox_repo()
    assert repo["id"] == "Orosius/deltanet-mla-latent" and repo["gated"] == "manual"
    assert len(repo["files"]) == 1018
    assert repo["files"][".gitattributes"]["oid"] == "a6344aac8c09253b3b630fb776ae94478aa0275b"
    assert repo["files"]["README.md"]["text"] == "---\r\nlicense: mit\r\n---\r\n"
    assert list(repo["info"])[:3] == ["tags", "downloads", "likes"]


def test_pinned_timestamps_cover_seeded_requests():
    pinned = pinned_timestamps(scenario_seed("ui-walkthrough"))
    assert {"2026-10-05T14:17:07.311Z", "2026-10-05T14:19:22.565Z", "2025-12-16T12:21:40.000Z"} <= pinned


def test_divergences_file_is_valid_and_globs_match():
    load_divergences()
    entry = Divergence("D-x", "live:*", "owner-*", "header:*", "Q-1", "test")
    diffs = compare_response(_step(*GATE_STEP).expected, Actual(500, {}, b""), ctx())
    apply_divergences("live:owner-reads", "owner-resolve", diffs, [entry])
    assert classify(diffs) == "fail"  # status and body are not covered by header:*
    assert all(d.divergence == "D-x" for d in diffs if d.field.startswith("header:"))


# --- stale divergences -----------------------------------------------------------------------------

def _result(name: str, diffs_by_step: dict[str, list], error: str | None = None):
    from conformance.compare import Diff
    from conformance.replay import ScenarioResult, StepResult

    step = _step(*GATE_STEP)
    result = ScenarioResult(name, "x.json", [], False, "seeded", error=error)
    for step_id, fields in diffs_by_step.items():
        diffs = [Diff(field, 1, 2) for field in fields]
        result.steps.append(StepResult(step, "fail" if diffs else "pass", diffs))
        result.steps[-1].step = type(step)(**{**vars(step), "id": step_id})
    return result


def test_stale_divergence_detection():
    from conformance.replay import stale_divergences, stale_message

    used = Divergence("D-used", "scen-a", "s1", "status", "R", "used")
    unused = Divergence("D-unused", "scen-a", "s2", "*", "R", "nothing to cover")
    other_run = Divergence("D-elsewhere", "live:*", "*", "*", "R", "scenario not in this run")
    errored = Divergence("D-errored", "scen-b", "*", "*", "R", "scenario failed to seed")
    rule = Divergence("D-rule", "rules:test_x", "test_y", "*", "R", "strict xfail instead")
    entries = [used, unused, other_run, errored, rule]
    results = [_result("scen-a", {"s1": ["status"], "s2": []}), _result("scen-b", {}, error="seed refused")]
    for result in results:
        for step_result in result.steps:
            apply_divergences(result.name, step_result.step.id, step_result.diffs, entries)
    assert [entry.id for entry in stale_divergences(results, entries)] == ["D-unused"]
    assert stale_message(unused).startswith("stale divergence D-unused: remove or re-justify")
    # once the mismatch it was written for comes back, the entry is no longer stale
    again = [_result("scen-a", {"s1": ["status"], "s2": ["body"]})]
    for step_result in again[0].steps:
        apply_divergences("scen-a", step_result.step.id, step_result.diffs, entries)
    assert stale_divergences(again, entries) == []


def test_stale_divergence_fails_the_report(monkeypatch, tmp_path):
    import conformance.report as report

    entry = Divergence("D-9", "scen-a", "s2", "*", "R", "nothing to cover")
    monkeypatch.setattr(report, "load_divergences", lambda: [entry])
    monkeypatch.setattr(report, "scenario_names", lambda: ["scen-a"])
    monkeypatch.setattr(report, "run_scenarios", lambda names, client, live=False: [_result("scen-a", {"s1": []})])
    monkeypatch.setattr(report, "load_manifest", lambda: {"scenarios": {}})
    monkeypatch.setenv("BACKEND_URL", os.environ.get("BACKEND_URL", "http://127.0.0.1:8200"))  # restored after
    assert report.main(["--out", str(tmp_path / "r"), "--backend", "http://127.0.0.1:1"]) == 1
    markdown = (tmp_path / "r.md").read_text()
    assert "stale divergence D-9: remove or re-justify" in markdown and "Overall: **FAIL**" in markdown


def test_saved_run_is_rejudged_against_current_divergences():
    from conformance.replay import results_from_json

    step = load_recording("2026-10-05-clone-seed-reads.json").steps[0]
    payload = {"scenarios": [{
        "name": "live:clone-seed-reads", "recording": "2026-10-05-clone-seed-reads.json", "covers": [],
        "stand_ins": True, "mode": "live", "error": None,
        "steps": [{"id": step.id, "outcome": "diverged", "reason": "", "actual_status": 200, "restricted_to": None,
                   "diffs": [{"field": "header:content-type", "expected": "a", "actual": "b", "detail": "",
                              "divergence": "D-old"}]}],
    }]}
    [result] = results_from_json(payload, [])  # the entry that covered it is gone
    assert result.steps[0].outcome == "fail" and not result.ok
    entry = Divergence("D-new", "live:*", step.id, "header:content-type", "R", "still needed")
    [result] = results_from_json(payload, [entry])
    assert result.steps[0].outcome == "diverged" and result.ok
