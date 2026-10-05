"""The authorisation decision on content routes (behaviour.md §2-§3, api.md §3.1-3.2).

Demo repos are ours (rule_seeds.py). Expected texts are HF's recorded ones (expect.py).
"""

from __future__ import annotations

import pytest

from conformance import expect as E
from conformance.rule_seeds import (ALLOWLISTED, AUTO, MANUAL, NOT_ALLOWLISTED, PUBLIC, REQUESTER, rules_seed,
                                    text_file)
from conformance.seeds import request


@pytest.fixture
def seeded(be):
    be.put_state(rules_seed())
    return be


@pytest.mark.parametrize("path", ALLOWLISTED)
@pytest.mark.parametrize("persona", ["anonymous", "requester"])
@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_ACC_5_allowlist_served_without_access(seeded, path, persona, method):
    response = seeded.resolve(MANUAL, path, persona, method=method)
    E.assert_ok(response)
    if method == "GET":
        assert response.content == text_file(path)["text"].encode(), E.describe(response)
    else:
        assert response.content == b""


@pytest.mark.parametrize("path", NOT_ALLOWLISTED)
@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_ACC_5_not_allowlisted_anonymous_is_401(seeded, path, method):
    # ACC-3 / api.md §3.1: anonymous -> 401 GatedRepo with WWW-Authenticate, text body on resolve
    response = seeded.resolve(MANUAL, path, "anonymous", method=method)
    E.assert_error(response, 401, E.gate_anonymous(MANUAL), code="GatedRepo", body="text", www_authenticate=True)


@pytest.mark.parametrize("path", NOT_ALLOWLISTED)
def test_ACC_5_not_allowlisted_requester_without_request_is_403(seeded, path):
    response = seeded.resolve(MANUAL, path, "requester")
    E.assert_error(response, 403, E.gate_no_request(MANUAL), code="GatedRepo", body="text")


@pytest.mark.parametrize("path", ["README.md", "config.json"])
def test_ACC_5_allowlist_applies_in_auto_mode_too(seeded, path):
    response = seeded.resolve(AUTO, path, "anonymous")
    if path == "README.md":
        E.assert_ok(response)
    else:
        E.assert_error(response, 401, E.gate_anonymous(AUTO), code="GatedRepo", body="text", www_authenticate=True)


@pytest.mark.parametrize("persona,status,message", [
    ("anonymous", 401, E.gate_anonymous),
    ("requester", 403, E.gate_no_request),
])
@pytest.mark.parametrize("rev,path", [("main", "does-not-exist.bin"), ("nonexistent-branch", "config.json"),
                                      ("main", "sub/missing/LICENSE.txt")])
def test_ACC_6_gate_checked_before_existence(seeded, persona, status, message, rev, path):
    response = seeded.resolve(MANUAL, path, persona, rev=rev)
    E.assert_error(response, status, message(MANUAL), code="GatedRepo", body="text")


@pytest.mark.parametrize("persona", ["anonymous", "requester"])
@pytest.mark.parametrize("path", ["LICENSE", "LICENSE.md"])
def test_ACC_6_allowlisted_missing_file_is_404_entry_not_found(be, persona, path):
    document = rules_seed()
    repo = next(r for r in document["repos"] if r["id"] == AUTO)  # AUTO has only README.md and config.json
    assert path not in repo["files"]
    be.put_state(document)
    response = be.resolve(AUTO, path, persona)
    E.assert_error(response, 404, E.ENTRY_NOT_FOUND, code="EntryNotFound", body="text")


@pytest.mark.parametrize("repo", [MANUAL, AUTO])
def test_ACC_1_owner_bypasses_gate(seeded, repo):
    check = seeded.auth_check(repo, "owner")
    E.assert_ok(check)
    assert check.text == "OK"
    E.assert_ok(seeded.resolve(repo, "config.json", "owner"))
    E.assert_ok(seeded.resolve(repo, "config.json", "owner", method="HEAD"))
    # bypassing creates no request (lists stay empty)
    for status in ("pending", "accepted", "rejected", "reset"):
        assert seeded.list_requests(repo, status).json() == []


STATES = {
    "no request": (None, 403, E.gate_no_request),
    "pending": ("pending", 403, E.gate_pending),
    "rejected": ("rejected", 403, E.gate_rejected),
    "reset": ("reset", 403, E.gate_reset),
    "accepted": ("accepted", 200, None),
}


@pytest.mark.parametrize("state", list(STATES))
def test_states_same_answer_on_auth_check_resolve_get_and_head(be, state):
    # behaviour.md §2: "The content-route answer is the same on auth-check, resolve GET and HEAD."
    status_name, status, message = STATES[state]
    requests = []
    if status_name:
        reviewed = None if status_name == "pending" else "2026-10-05T14:10:00.000Z"
        granted = "Orosius" if status_name == "accepted" else None
        requests = [request(REQUESTER, status_name, "2026-10-05T14:00:00.000Z", reviewed, granted, repo=MANUAL)]
    be.put_state(rules_seed(requests))
    check = be.auth_check(MANUAL, "requester")
    get = be.resolve(MANUAL, "config.json", "requester")
    head = be.resolve(MANUAL, "config.json", "requester", method="HEAD")
    if status == 200:
        E.assert_ok(check)
        assert check.text == "OK"
        E.assert_ok(get)
        assert get.content == text_file("config.json")["text"].encode()
        E.assert_ok(head)
    else:
        E.assert_error(check, status, message(MANUAL), code="GatedRepo", body="json")
        E.assert_error(get, status, message(MANUAL), code="GatedRepo", body="text")
        E.assert_error(head, status, message(MANUAL), code="GatedRepo", body="text")
        assert head.content == b""


def test_ACC_3_anonymous_auth_check_on_gated_repo(seeded):
    response = seeded.auth_check(MANUAL, "anonymous")
    E.assert_error(response, 401, E.gate_anonymous(MANUAL), code="GatedRepo", body="json", www_authenticate=True)


def test_ACC_4_metadata_and_tree_stay_public(seeded):
    info = seeded.get("anonymous", f"/api/models/{MANUAL}")
    E.assert_ok(info)
    assert info.json()["gated"] == "manual"
    tree = seeded.get("anonymous", f"/api/models/{MANUAL}/tree/main")
    E.assert_ok(tree)
    paths = {entry["path"] for entry in tree.json()}
    assert {"README.md", "config.json", "sub"} <= paths
    expand = seeded.get("anonymous", f"/api/models/{MANUAL}?expand[]=gated&expand[]=cardData")
    # model-info-expand [OBS]: expand[] selects fields, in this order
    assert list(expand.json()) == ["_id", "id", "gated", "cardData"], E.describe(expand)


@pytest.mark.parametrize("persona", ["anonymous", "requester"])
def test_ACC_7_CFG_5_not_gated_auth_check_is_ok(seeded, persona):
    # CFG-5: stale extra_gated_description has no effect; CFG-6 [OBS s10-req-auth-check, auth-check-public]
    check = seeded.auth_check(PUBLIC, persona)
    E.assert_ok(check)
    assert check.text == "OK"


def test_ACC_7_not_gated_anonymous_resolve_redirects_to_resolve_cache(seeded):
    # owner-walkthrough s10-anon-resolve [OBS]: 307 to /api/resolve-cache/models/{id}/{sha}/{path}?...&etag="oid"
    response = seeded.resolve(PUBLIC, "config.json", "anonymous")
    assert response.status_code == 307, E.describe(response)
    state_repo = next(r for r in rules_seed()["repos"] if r["id"] == PUBLIC)
    location = response.headers["location"]
    prefix = f"/api/resolve-cache/models/{PUBLIC}/{state_repo['sha']}/config.json?"
    assert location.startswith(prefix), location
    oid = state_repo["files"]["config.json"]["oid"]
    assert location.endswith(f"=&etag=%22{oid}%22"), location
    cached = seeded.req("anonymous", "GET", location)  # system.md: the clone serves the redirect target
    E.assert_ok(cached)
    assert cached.content == text_file("config.json")["text"].encode()


def test_ACC_8_revoked_user_loses_access(be):
    be.put_state(rules_seed())
    E.assert_ok(be.grant(MANUAL, {"user": REQUESTER}))
    E.assert_ok(be.resolve(MANUAL, "config.json", "requester"))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "pending"}))
    E.assert_error(be.resolve(MANUAL, "config.json", "requester"), 403, E.gate_pending(MANUAL), code="GatedRepo",
                   body="text")
