"""Fixture smoke: replay recorded exchanges against the clone, from the matching initial state.

Ground truth = docs/hf-gated/observations/*.json. Compared: status, X-Error-Code, X-Error-Message,
Location, Content-Type, Content-Disposition, and the body (JSON equal after normalising redacted
e-mails and the times the virtual clock cannot reproduce; text bodies by their recorded prefix).
"""

from __future__ import annotations

from urllib.parse import urlsplit

import pytest
from clone.app import create_app
from clone.store import Store
from conftest import PUBLIC_URL, auth, load_observation, request_entry, sandbox_with
from fastapi.testclient import TestClient

AS = {"OWNER": "owner", "HF_OWNER_ACCESS_TOKEN": "owner", "REQUESTER": "requester",
      "HF_REQUESTER_ACCESS_TOKEN": "requester", "anonymous": None, "BAD_TOKEN": "not-a-token"}
EMAIL = "<email>"
CHECKED_HEADERS = ("x-error-code", "x-error-message", "location", "content-type", "content-disposition")


def normalise(value, times: set[str]):
    """Redacted e-mails as recorded; the listed time keys blanked (their presence still counts)."""
    if isinstance(value, list):
        return [normalise(v, times) for v in value]
    if isinstance(value, dict):
        return {k: EMAIL if k == "email" else "<time>" if k in times else normalise(v, times)
                for k, v in value.items()}
    return value


class Replayer:
    def __init__(self, store: Store, public_url: str = PUBLIC_URL):
        self.store = store
        self.client = TestClient(create_app(store, public_url=public_url), follow_redirects=False)

    def send(self, *, method, path, query="", persona=None, body=None, encoding="json"):
        kwargs = {"headers": auth(persona)}
        if body is not None:
            kwargs["data" if encoding == "form" else "json"] = body
        return self.client.request(method, path + (f"?{query}" if query else ""), **kwargs)

    def redact(self, text: str) -> str:
        for u in self.store.users.values():
            text = text.replace(u["email"], EMAIL)
        return text.replace("<HF_REQUESTER_LOGIN>", EMAIL)

    def check(self, resp, *, status, headers, body_json=None, body_text=None, times=frozenset(), label=""):
        assert resp.status_code == status, label
        for name in CHECKED_HEADERS:
            assert resp.headers.get(name) == headers.get(name), f"{label}: {name}"
        if body_json is not None:
            assert normalise(resp.json(), times) == normalise(body_json, times), label
        elif body_text:
            assert self.redact(resp.text).startswith(self.redact(body_text)), label


# --- 1. probe.py recordings (owner/requester walkthroughs), replayed in order --------------------------

PROBE_FILES = {
    # name: (initial requests, times the virtual clock cannot reproduce, public URL of the recording)
    # s0 starts with no request at all [OBS W s0].
    "2026-10-05-owner-walkthrough.json": ([], {"timestamp", "reviewedAt", "time"}, PUBLIC_URL),
    # m0: pending since the walkthrough's re-request; that timestamp never changes (TS-1), so it is
    # compared exactly.
    "2026-10-05-owner-walkthrough-completion.json": (
        [request_entry("pending", "2026-10-05T14:17:07.311Z")], {"reviewedAt"}, PUBLIC_URL),
    # These two were recorded directly against huggingface.co (no bridge rewriting Location).
    "2026-10-05-requester-ask-access.json": ([], set(), "https://huggingface.co"),
    "2026-10-05-owner-reads.json": ([request_entry("pending", "2026-10-05T13:31:55.250Z")], set(),
                                    "https://huggingface.co"),
}
NOT_BACKEND = {"pre-page"}  # the HTML model page belongs to the web app, not to the backend


@pytest.mark.parametrize("name", PROBE_FILES)
def test_probe_recording_replay(name):
    requests, times, public_url = PROBE_FILES[name]
    replayer = Replayer(Store(sandbox_with(requests)), public_url)
    for r in load_observation(name)["records"]:
        if r["id"] in NOT_BACKEND:
            continue
        url = urlsplit(r["url"])
        resp = replayer.send(method=r["method"], path=url.path, query=url.query, persona=AS[r["as"]],
                             body=r["request_body"], encoding=r["request_encoding"])
        replayer.check(resp, status=r["status"], headers=r["headers"], body_json=r.get("body_json"),
                       body_text=r.get("body_excerpt"), times=times, label=r["id"])


# --- 2. the UI walkthrough (bridge exchange log) ------------------------------------------------------


def test_ui_walkthrough_replay():
    """62 requests the web UI fired through the bridge. Initial state = the end of the completion
    walkthrough: TestingBOrig `reset` [OBS C m8, UI #193]. The clone's own log entries must have the
    bridge's schema (same keys, same order) and record the same exchanges."""
    log = load_observation("2026-10-05-ui-walkthrough.json")
    store = Store(sandbox_with([request_entry("reset", "2026-10-05T14:17:07.311Z",
                                              reviewedAt="2026-10-05T14:19:22.565Z")]))
    replayer = Replayer(store)
    for e in log:
        resp = replayer.send(method=e["method"], path=e["path"], query=e["query"], persona=e["persona"],
                             body=e["request_body"])
        body = e["response_body"]
        replayer.check(resp, status=e["status"], headers={k.lower(): v for k, v in e["response_headers"].items()},
                       body_json=body if isinstance(body, (dict, list)) else None,
                       body_text=body if isinstance(body, str) else None,
                       times={"timestamp", "reviewedAt"}, label=f"#{e['id']}")
    ours = list(store.log)
    assert [list(o) for o in ours] == [list(e) for e in log]
    assert [(o["persona"], o["method"], o["path"], o["query"], o["status"], o["upstream"]) for o in ours] == \
        [(e["persona"], e["method"], e["path"], e["query"], e["status"], False) for e in log]


# --- 3. direct reads of the sandbox (probe.py against huggingface.co) --------------------------------

SEED_READS = "2026-10-05-clone-seed-reads.json"
NOT_SEEDED = {"owner-not-gated-list"}  # openai-community/gpt2 is not in the seed
REDIRECT_TARGET_DIFFERS = {"owner-head-lfs"}  # checked separately below
REDACTED_BODY = {"whoami-owner", "whoami-requester"}  # e-mails redacted: ETag/length cannot match


@pytest.mark.parametrize("record", [pytest.param(r, id=r["id"]) for r in load_observation(SEED_READS)["records"]
                                    if r["id"] not in NOT_SEEDED | REDIRECT_TARGET_DIFFERS])
def test_seed_reads_byte_for_byte(store, record):
    """Model info, tree, whoami, file contents and their headers, as recorded. ETag and
    Content-Length equal means the same bytes."""
    replayer = Replayer(store, "https://huggingface.co")
    url = urlsplit(record["url"])
    resp = replayer.send(method=record["method"], path=url.path, query=url.query, persona=AS[record["as"]])
    headers = record["headers"]
    replayer.check(resp, status=record["status"], headers=headers, body_json=record.get("body_json"),
                   body_text=record.get("body_text") or record.get("body_excerpt"), label=record["id"])
    if "text/html" in headers["content-type"]:
        return  # HF's HTML error page; the clone sends only the message (provisional)
    if record["id"] not in REDACTED_BODY:
        assert (resp.headers["etag"], resp.headers["content-length"]) == (headers["etag"], headers["content-length"])
    assert resp.headers.get("x-repo-commit") == headers.get("x-repo-commit")
    if "body_text" in record:
        assert resp.text == record["body_text"]


def test_lfs_redirect_headers(store):
    """[OBS owner-head-lfs]: 302 with X-Linked-Size, X-Linked-Etag, X-Repo-Commit. Provisional:
    the target is the clone's own resolve-cache instead of HF's CDN."""
    (record,) = [r for r in load_observation(SEED_READS)["records"] if r["id"] == "owner-head-lfs"]
    resp = Replayer(store).send(method="HEAD", path=urlsplit(record["url"]).path, persona="owner")
    assert resp.status_code == 302
    for name in ("x-linked-size", "x-linked-etag", "x-repo-commit", "content-type"):
        assert resp.headers[name] == record["headers"][name]
    assert resp.headers["location"].startswith(f"{PUBLIC_URL}/api/resolve-cache/models/{record['url'].split('/')[3]}/")
