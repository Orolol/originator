"""Clone contract: control endpoints, virtual clock, exchange log, determinism (docs/system.md).

These are not HF behaviour; they are what makes the clone testable. HF behaviour inside them
(timestamps per TS-1/TS-2) is asserted against the virtual clock.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from conformance import expect as E
from conformance.clone_api import snapshot
from conformance.compare import Context, TimestampTracker, compare_response
from conformance.config import OBSERVATIONS, RECORDED_ORIGINS
from conformance.recordings import load_recording
from conformance.divergences import load_divergences
from conformance.replay import apply_divergences, to_actual
from conformance.rule_seeds import CAROL, MANUAL, NOW, REQUESTER, rules_seed
from conformance.seeds import SANDBOX

# system.md: "same entry schema as /__bridge__/log"; the key order is the bridge's, as recorded in
# observations/2026-10-05-ui-walkthrough.json (a /__bridge__/log export).
LOG_KEYS = list(json.loads((OBSERVATIONS / "2026-10-05-ui-walkthrough.json").read_text())[0])


def plus(iso: str, ms: int) -> str:
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00")) + timedelta(milliseconds=ms)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def test_health(be):
    be.put_state(rules_seed())
    health = be.health()
    assert health.get("ok") is True, health
    assert {"seed", "now"} <= set(health), health
    assert health["now"] == NOW


def test_reset_restores_default_sandbox_seed(be):
    assert be.reset().status_code < 300
    baseline = be.state()
    # system.md: built-in `sandbox` seed = recorded sandbox repo, TestingBOrig pending
    pending = be.list_requests(SANDBOX, "pending").json()
    assert [item["user"]["user"] for item in pending] == [REQUESTER], pending
    E.assert_ok(be.handle(SANDBOX, {"user": REQUESTER, "status": "accepted"}))
    be.ask(SANDBOX, persona="carol")
    assert be.reset().status_code < 300
    assert be.state() == baseline
    assert be.log() == [] and be.outbox() == []
    assert be.reset("sandbox").status_code < 300
    assert be.state() == baseline


@pytest.mark.parametrize("recording", ["clone-seed-reads", "tree-masking"])
def test_builtin_sandbox_seed_reproduces_recorded_reads(be, recording):
    # The default seed must serve what anonymous callers were recorded getting (model info, tree with ACC-9
    # masking, files, gate answers), with the same accepted divergences as the replay of that recording.
    assert be.reset().status_code < 300
    steps = load_recording(f"2026-10-05-{recording}.json").steps
    ctx = Context(TimestampTracker(set()), be.base_url, RECORDED_ORIGINS)
    divergences = load_divergences()
    problems = {}
    for step in steps:
        if step.persona != "anonymous":
            continue
        response = be.req(step.persona, step.method, step.path)
        diffs = compare_response(step.expected, to_actual(response), ctx)
        apply_divergences(recording, step.id, diffs, divergences)
        diffs = [d for d in diffs if d.divergence is None]
        if diffs:
            problems[step.id] = [(d.field, d.expected, d.actual) for d in diffs[:5]]
    assert not problems, problems


def test_builtin_demo_repos_and_carol(be):
    # system.md "Built-in seeds": demo repos owned by Orosius and the third user DemoCarol
    assert be.reset().status_code < 300
    for repo, gated in (("Orosius/gated-auto-demo", "auto"), ("Orosius/gated-form-demo", "manual"),
                        ("Orosius/not-gated-demo", False)):
        response = be.get("anonymous", f"/api/models/{repo}?expand[]=gated")
        E.assert_ok(response)
        assert response.json()["gated"] == gated, response.text
    whoami = be.get("carol", "/api/whoami-v2")
    E.assert_ok(whoami)
    assert whoami.json()["name"] == CAROL


def test_state_round_trip_and_put_clears_log_and_outbox(be):
    document = rules_seed()
    be.put_state(document)
    be.ask(MANUAL)
    assert be.log() and be.outbox()
    state = be.state()
    be.put_state(state)
    assert be.state() == state
    assert be.log() == [] and be.outbox() == []
    # what we seeded is what the state reports for the request we created
    requests = [r for r in state["requests"] if r["repo"] == MANUAL]
    assert [(r["user"], r["status"]) for r in requests] == [(REQUESTER, "pending")]


def test_clock_set_advance_and_reads_do_not_tick(be):
    be.put_state(rules_seed())
    assert be.clock()["now"] == NOW
    be.list_requests(MANUAL, "pending")
    be.auth_check(MANUAL, "requester")
    assert be.clock()["now"] == NOW  # reads do not advance the clock
    assert be.set_clock({"now": "2026-10-06T08:00:00.000Z"}).status_code < 300
    assert be.clock()["now"] == "2026-10-06T08:00:00.000Z"
    assert be.set_clock({"advance_ms": 1500}).status_code < 300
    assert be.clock()["now"] == "2026-10-06T08:00:01.500Z"


def test_state_changes_tick_before_stamping(be):
    # system.md: each state-changing request advances the clock by tick_ms BEFORE stamping; TS-1/TS-2
    be.put_state(rules_seed(tick_ms=1000))
    assert be.ask(MANUAL).status_code == 303
    item = be.list_requests(MANUAL, "pending").json()[0]
    assert item["timestamp"] == plus(NOW, 1000)
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "accepted"}))
    item = be.list_requests(MANUAL, "accepted").json()[0]
    assert (item["timestamp"], item["reviewedAt"]) == (plus(NOW, 1000), plus(NOW, 2000))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "reset", "resetReason": "again"}))
    item = be.list_requests(MANUAL, "reset").json()[0]
    assert (item["timestamp"], item["reviewedAt"]) == (plus(NOW, 1000), plus(NOW, 3000))
    assert be.ask(MANUAL).status_code == 303
    item = be.list_requests(MANUAL, "pending").json()[0]
    assert item["timestamp"] == plus(NOW, 4000) and "reviewedAt" not in item  # TS-1: new timestamp after reset
    assert be.clock()["now"] == plus(NOW, 4000)


def test_failed_writes_do_not_tick(be):
    be.put_state(rules_seed())
    E.assert_error(be.handle(MANUAL, {"user": CAROL, "status": "accepted"}), 404, E.NO_REQUEST)
    assert be.handle(MANUAL, {"user": REQUESTER, "status": "bogus"}).status_code == 400
    assert be.clock()["now"] == NOW


def test_log_entries_follow_bridge_schema(be):
    be.put_state(rules_seed())
    be.get("anonymous", f"/api/models/{MANUAL}?expand[]=gated")
    be.ask(MANUAL)
    be.handle(MANUAL, {"user": REQUESTER, "status": "accepted"})
    log = be.log()
    assert len(log) == 3, log
    assert set(LOG_KEYS) == {"id", "started_at", "duration_ms", "persona", "method", "path", "query", "request_body",
                             "status", "response_headers", "response_body", "upstream"}  # system.md list
    assert all(list(entry) == LOG_KEYS for entry in log), [list(e) for e in log]
    assert [(e["persona"], e["method"], e["path"], e["status"]) for e in log] == [
        ("anonymous", "GET", f"/api/models/{MANUAL}", 200),
        ("requester", "POST", f"/{MANUAL}/ask-access", 303),
        ("owner", "POST", f"/api/models/{MANUAL}/user-access-request/handle", 200),
    ]
    assert log[0]["query"] == "expand[]=gated" or log[0]["query"] == "expand%5B%5D=gated", log[0]["query"]
    assert log[2]["request_body"] == {"user": REQUESTER, "status": "accepted"}
    started = [e["started_at"] for e in log]
    assert started[0] == NOW and started == sorted(started), started  # virtual clock, not wall clock
    assert started[-1] <= be.clock()["now"], started
    assert all(e["duration_ms"] == 0 for e in log)
    assert be.clear_log().status_code < 300 and be.log() == []


SEQUENCE = [
    ("requester", "POST", f"/{MANUAL}/ask-access", {}),
    ("owner", "GET", f"/api/models/{MANUAL}/user-access-request/pending", None),
    ("owner", "POST", f"/api/models/{MANUAL}/user-access-request/handle", {"user": REQUESTER, "status": "rejected"}),
    ("requester", "GET", f"/api/models/{MANUAL}/auth-check", None),
    ("owner", "POST", f"/api/models/{MANUAL}/user-access-request/grant", {"user": CAROL}),
    ("owner", "POST", f"/api/models/{MANUAL}/user-access-request/handle",
     {"user": REQUESTER, "status": "reset", "resetReason": "again"}),
    ("requester", "POST", f"/{MANUAL}/ask-access", {}),
    ("owner", "POST", f"/api/models/{MANUAL}/user-access-request/batch",
     {"status": "accepted", "requests": [{"user": REQUESTER}, {"user": "nobody-xyz"}]}),
    ("owner", "GET", f"/{MANUAL}/user-access-report", None),
    ("owner", "GET", f"/api/models/{MANUAL}/user-access-request/accepted?limit=10", None),
    ("anonymous", "GET", f"/{MANUAL}/resolve/main/config.json", None),
    ("carol", "GET", f"/{MANUAL}/resolve/main/config.json", None),
]


def _run(be) -> dict:
    be.put_state(rules_seed())
    responses = [snapshot(be.req(persona, method, path, body)) for persona, method, path, body in SEQUENCE]
    return {"responses": responses, "log": be.log(), "outbox": be.outbox(), "state": be.state()}


def test_determinism_same_seed_same_sequence(be):
    first, second = _run(be), _run(be)
    for key in ("responses", "log", "outbox", "state"):
        assert first[key] == second[key], key
