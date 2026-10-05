"""Control endpoints and determinism (docs/system.md "Clone: contract"): reset, state round-trip,
virtual clock, log and outbox; plus the built-in seed staying in sync with the fixtures."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from clone.app import create_app
from clone.store import Store, builtin_seed
from conftest import REPO, auth
from fastapi.testclient import TestClient

LIST = f"/api/models/{REPO}/user-access-request"

# A scripted session mixing writes and reads, by owner, requester, a granted user and anonymous.
SCRIPT = [
    ("owner", "POST", f"{LIST}/handle", {"user": "TestingBOrig", "status": "accepted"}),
    ("requester", "GET", f"/{REPO}/resolve/main/.gitattributes", None),
    ("owner", "POST", f"{LIST}/grant", {"user": "DemoCarol"}),
    ("owner", "POST", f"{LIST}/batch", {"status": "reset", "resetReason": "again", "requests": [
        {"user": "TestingBOrig"}, {"userId": "c6b12968e29b4c68d1684f14"}, {"user": "ghost"}]}),
    ("requester", "POST", f"/{REPO}/ask-access", {}),
    ("owner", "PUT", f"/api/models/{REPO}/settings", {"gated": "auto", "gatedNotificationsMode": "real-time"}),
    ("carol", "POST", "/Orosius/gated-form-demo/ask-access", {"First Name": "Carol"}),
    (None, "GET", f"/api/models/{REPO}/auth-check", None),
    ("owner", "GET", f"{LIST}/pending", None),
    ("owner", "GET", f"{LIST}/reset", None),
    ("owner", "GET", f"/{REPO}/user-access-report", None),
]


def run_script(client: TestClient) -> list:
    out = []
    for persona, method, path, body in SCRIPT:
        resp = client.request(method, path, json=body, headers=auth(persona))
        out.append((resp.status_code, dict(resp.headers), resp.content))
    return out


def test_same_sequence_same_bytes():
    """Same seed + same requests ⇒ byte-identical responses, log and outbox, across a reset and
    across processes (two app instances)."""
    # The script starts from the recorded state (TestingBOrig pending), i.e. the `sandbox` seed.
    a = TestClient(create_app(Store(builtin_seed("sandbox"))), follow_redirects=False)
    first = (run_script(a), a.get("/__clone__/log?limit=1000").json(), a.get("/__clone__/outbox").json())
    assert a.post("/__clone__/reset", json={"seed": "sandbox"}).json()["now"] == "2026-10-05T14:30:00.000Z"
    second = (run_script(a), a.get("/__clone__/log?limit=1000").json(), a.get("/__clone__/outbox").json())
    b = TestClient(create_app(Store(builtin_seed("sandbox"))), follow_redirects=False)
    third = (run_script(b), b.get("/__clone__/log?limit=1000").json(), b.get("/__clone__/outbox").json())
    assert first == second == third
    # batch reset e-mails both users; the re-request after reset and Carol's form request notify the owner
    assert [(o["kind"], o["user"]) for o in first[2]] == [
        ("request_reset", "TestingBOrig"), ("request_reset", "DemoCarol"),
        ("new_request", "TestingBOrig"), ("new_request", "DemoCarol")]


def test_state_round_trip(client):
    run_script(client)
    state = client.get("/__clone__/state").json()
    reads = [client.get(p, headers=auth("owner")).content for p in (f"{LIST}/pending", f"{LIST}/reset")]
    assert client.put("/__clone__/state", json=state).json()["ok"] is True
    assert client.get("/__clone__/state").json() == state
    assert [client.get(p, headers=auth("owner")).content for p in (f"{LIST}/pending", f"{LIST}/reset")] == reads
    # PUT clears log and outbox (the GETs above were logged after it)
    assert client.get("/__clone__/outbox").json() == []
    assert [e["method"] for e in client.get("/__clone__/log").json()] == ["GET"] * 2


def test_reset_restores_a_named_seed(client):
    pristine = client.get("/__clone__/state").json()
    run_script(client)
    assert client.get("/__clone__/state").json() != pristine
    assert client.post("/__clone__/reset", json={"seed": "sandbox"}).json()["seed"] == "sandbox"
    assert client.get("/__clone__/state").json() == pristine
    assert client.get("/__clone__/log").json() == [] and client.get("/__clone__/outbox").json() == []
    unknown = client.post("/__clone__/reset", json={"seed": "nope"})
    assert unknown.status_code == 404 and unknown.json()["seeds"] == ["clean", "sandbox"]


def test_default_seed_is_clean():
    """A restart or a bare reset gives the `clean` seed: the sandbox's repos and users, no request."""
    client = TestClient(create_app(Store()), follow_redirects=False)
    state = client.get("/__clone__/state").json()
    assert (state["seed"], state["requests"]) == ("clean", [])
    sandbox = builtin_seed("sandbox")
    assert (state["repos"], state["users"]) == (sandbox["repos"], sandbox["users"])
    client.post(f"{LIST}/grant", json={"user": "TestingBOrig"}, headers=auth("owner"))
    assert client.post("/__clone__/reset").json()["seed"] == "clean"
    assert client.get("/__clone__/state").json()["requests"] == []
    for status in ("pending", "accepted", "rejected", "reset"):
        assert client.get(f"{LIST}/{status}", headers=auth("owner")).json() == []


def test_invalid_state_is_rejected_and_keeps_the_old_one(client):
    before = client.get("/__clone__/state").json()
    bad = dict(before, requests=[{"repo": REPO, "user": "ghost", "status": "pending", "timestamp": before["now"]}])
    resp = client.put("/__clone__/state", json=bad)
    assert resp.status_code == 400 and "unknown user" in resp.json()["error"]
    assert client.get("/__clone__/state").json() == before


def test_virtual_clock(client):
    """Reads never move the clock; each state change advances it by tick_ms before stamping;
    no-op writes do not change state, so they do not tick."""
    clock = lambda: client.get("/__clone__/clock").json()["now"]  # noqa: E731
    assert clock() == "2026-10-05T14:30:00.000Z"
    client.get(f"{LIST}/pending", headers=auth("owner"))
    client.post(f"/{REPO}/ask-access", json={}, headers=auth("requester"))  # pending re-submit: no-op [OBS]
    assert clock() == "2026-10-05T14:30:00.000Z"
    client.post(f"{LIST}/handle", json={"user": "TestingBOrig", "status": "accepted"}, headers=auth("owner"))
    assert clock() == "2026-10-05T14:30:01.000Z"
    (item,) = client.get(f"{LIST}/accepted", headers=auth("owner")).json()
    assert item["reviewedAt"] == "2026-10-05T14:30:01.000Z"
    assert client.post("/__clone__/clock", json={"advance_ms": 59_000}).json()["now"] == "2026-10-05T14:31:00.000Z"
    assert client.post("/__clone__/clock", json={"now": "2026-10-06T00:00:00Z"}).json()["now"] == \
        "2026-10-06T00:00:00.000Z"
    assert client.post("/__clone__/clock", json={"advance_ms": -1}).status_code == 400
    log = client.get("/__clone__/log").json()
    assert [e["started_at"] for e in log[-2:]] == ["2026-10-05T14:30:00.000Z", "2026-10-05T14:30:01.000Z"]
    assert client.get("/__clone__/health").json() == {"ok": True, "seed": "sandbox", "now": "2026-10-06T00:00:00.000Z"}


def test_builtin_seed_matches_the_fixtures():
    """The committed seed is exactly what clone/scripts/derive_seed.py derives from the fixtures."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "derive_seed.py"
    spec = importlib.util.spec_from_file_location("derive_seed", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert json.loads(json.dumps(module.build_seed())) == builtin_seed("sandbox")
    assert json.loads(json.dumps(module.build_clean_seed())) == builtin_seed("clean")
