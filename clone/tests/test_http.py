"""HTTP-level tests: the error matrix and check order (api.md §3), headers, and the behaviours the
recorded walkthroughs do not exercise (pagination, search, forms, outbox, provisional choices)."""

from __future__ import annotations

import pytest
from clone.app import create_app
from clone.store import Store, builtin_seed
from conftest import REPO, auth, request_entry, sandbox_with
from fastapi.testclient import TestClient

API = "application/json; charset=utf-8"
TEXT = "text/plain; charset=utf-8"
HTML = "text/html; charset=utf-8"
WWW = 'Bearer realm="Authentication required", charset="UTF-8"'
LIST = f"/api/models/{REPO}/user-access-request"
GATE_ANON = (f"Access to model {REPO} is restricted. You must have access to it and be authenticated to access "
             "it. Please log in.")
PENDING = f"Your request to access model {REPO} is awaiting a review from the repo authors."
NO_PERM = "You have read access but not the required permissions for this operation"
BAD_CREDS = "Invalid username or password."

# (persona, method, path, json body, status, X-Error-Code, X-Error-Message, Content-Type)
ERRORS = [
    # docs/system.md "Personas": any unknown bearer → 401, on every surface route, per route format
    ("bogus", "GET", "/api/whoami-v2", None, 401, None, BAD_CREDS, API),
    ("bogus", "GET", f"/api/models/{REPO}", None, 401, None, BAD_CREDS, API),
    ("bogus", "GET", f"/{REPO}/resolve/main/README.md", None, 401, None, BAD_CREDS, TEXT),
    ("bogus", "GET", f"/{REPO}/user-access-report", None, 401, None, BAD_CREDS, HTML),
    # api.md §3.3 check order: authentication, then repo, then permission, then validation
    (None, "GET", "/api/models/OwnerOfTheGatedModel/nope/user-access-request/pending", None, 401, None, BAD_CREDS, API),
    ("owner", "GET", "/api/models/OwnerOfTheGatedModel/nope/user-access-request/pending", None, 404, "RepoNotFound",
     "Repository not found", API),
    ("requester", "GET", f"{LIST}/pending?limit=5", None, 403, None, NO_PERM, API),
    ("carol", "PUT", f"/api/models/{REPO}/settings", {"gated": "auto"}, 403, None, NO_PERM, API),
    ("requester", "POST", f"{LIST}/grant", {"user": "DemoCarol"}, 403, None, NO_PERM, API),
    ("requester", "GET", f"/{REPO}/user-access-report", None, 403, None, NO_PERM, HTML),  # Provisional
    # REV-12 validation (no X-Error-Code)
    ("owner", "GET", f"{LIST}/pending?limit=1001", None, 400, None,
     "* Too big: expected number to be <=1000 * at limit", API),
    ("owner", "POST", f"{LIST}/handle", {"user": "TestingBOrig", "userId": "6ac3a4b8792f9017b6cb67ec",
                                         "status": "accepted"}, 400, None,
     "* Either userId or user must be provided, but not both", API),
    ("owner", "POST", f"{LIST}/grant", {}, 400, None, "* Either userId or user must be provided, but not both", API),
    ("owner", "PUT", f"/api/models/{REPO}/settings", {"gated": True}, 400, None, "* Invalid input * at gated", API),
    ("owner", "POST", f"{LIST}/batch", {"status": "accepted", "requests": []}, 400, None,
     "* Too small: expected array to have >=1 items * at requests", API),
    # REV-7, §5.1 lookups
    ("owner", "POST", f"{LIST}/handle", {"userId": "0123456789abcdef01234567", "status": "accepted"}, 404, None,
     "User not found", API),
    ("owner", "POST", f"{LIST}/handle", {"user": "DemoCarol", "status": "accepted"}, 404, None,
     "No access request found matching your criteria", API),
    # ACC-3, ACC-5, ACC-6 on resolve [OBS anonymous-probes, on other repos]
    (None, "GET", f"/{REPO}/resolve/main/readme.md", None, 401, "GatedRepo", GATE_ANON, TEXT),
    (None, "GET", f"/{REPO}/resolve/main/checkpoint-0/README.md", None, 401, "GatedRepo",
     GATE_ANON, TEXT),
    (None, "GET", f"/{REPO}/resolve/no-such-branch/no-such-file.bin", None, 401, "GatedRepo", GATE_ANON, TEXT),
    ("requester", "GET", f"/{REPO}/resolve/no-such-branch/config.json", None, 403, "GatedRepo", PENDING, TEXT),
    (None, "GET", f"/{REPO}/resolve/main/LICENSE.md", None, 404, "EntryNotFound", "Entry not found", TEXT),
    (None, "GET", f"/{REPO}/resolve/v9/README.md", None, 404, "RevisionNotFound", "Revision not found", TEXT),
    (None, "GET", f"/api/models/{REPO}/auth-check", None, 401, "GatedRepo", GATE_ANON, API),
    # ACC-10 [OBS tree-masking raw-*]: raw has resolve's gate and messages, but no allowlist
    (None, "GET", f"/{REPO}/raw/main/README.md", None, 401, "GatedRepo", GATE_ANON, TEXT),
    ("requester", "GET", f"/{REPO}/raw/main/README.md", None, 403, "GatedRepo", PENDING, TEXT),
    (None, "GET", f"/{REPO}/raw/no-such-branch/x.bin", None, 401, "GatedRepo", GATE_ANON, TEXT),
    ("owner", "GET", f"/{REPO}/raw/main/LICENSE", None, 404, "EntryNotFound", "Entry not found", TEXT),
    # Provisional (Q-1): anonymous ask-access is an authentication error
    (None, "POST", f"/{REPO}/ask-access", {}, 401, None, BAD_CREDS, HTML),
    # Outside the surface: HF's 404 page [OBS owner-get-settings]
    ("owner", "DELETE", f"/api/models/{REPO}/settings", None, 404, None,
     "Sorry, we can't find the page you are looking for.", API),
]


@pytest.mark.parametrize(("persona", "method", "path", "body", "status", "code", "message", "ctype"), ERRORS,
                         ids=[f"{e[1]} {e[2]} as {e[0]}" for e in ERRORS])
def test_error_matrix(client, persona, method, path, body, status, code, message, ctype):
    resp = client.request(method, path, json=body, headers=auth(persona))
    assert (resp.status_code, resp.headers.get("x-error-code"), resp.headers.get("x-error-message"),
            resp.headers["content-type"]) == (status, code, message, ctype)
    assert resp.headers.get("www-authenticate") == (WWW if status == 401 else None)
    if ctype == API:
        # REV-12: validation errors have zod's pretty body; the others repeat the message
        assert resp.json()["error"].startswith("✖" if message.startswith("* ") else message)


def test_head_mirrors_get_without_body(client):
    for path, persona in ((f"/{REPO}/resolve/main/.gitattributes", "requester"),
                          (f"/{REPO}/resolve/main/README.md", None)):
        get, head = (client.request(m, path, headers=auth(persona)) for m in ("GET", "HEAD"))
        assert head.status_code == get.status_code and head.content == b""
        assert dict(head.headers) == dict(get.headers)  # Content-Length included [OBS]


def test_REV_10_pagination_and_search():
    users = [{"user": f"user{i:02d}", "_id": f"{i:024x}", "fullname": f"Person {i}", "email": f"u{i}@corp{i % 2}.org",
              "avatarUrl": "/avatars/x.svg", "isPro": False, "token": f"tok-{i}", "orgs": []} for i in range(12)]
    seed = sandbox_with([request_entry("pending", f"2026-10-05T10:00:{i:02d}.000Z", user=u["user"])
                         for i, u in enumerate(users)])
    seed["users"] += users
    client = TestClient(create_app(Store(seed), public_url="http://clone.test"), follow_redirects=False)
    owner = auth("owner")
    first = client.get(f"{LIST}/pending?limit=10&q=user", headers=owner)
    assert [i["user"]["user"] for i in first.json()] == [f"user{i:02d}" for i in range(10)]
    # Provisional (Q-10): next page = after the last timestamp, other parameters kept
    assert first.headers["link"] == (f'<http://clone.test{LIST}/pending?limit=10&q=user&after='
                                     f'2026-10-05T10%3A00%3A09.000Z>; rel="next"')
    nxt = client.get(first.headers["link"][1:].split(">")[0].removeprefix("http://clone.test"), headers=owner)
    assert [i["user"]["user"] for i in nxt.json()] == ["user10", "user11"] and "link" not in nxt.headers
    # [OBS 2026-10-06 edge-cases-a e0-search-*]: case-insensitive prefix of the username only
    for q, count in (("USER0", 10), ("user1", 2), ("ser0", 0), ("person 1", 0), ("corp1.org", 0), ("zzz", 0)):
        assert len(client.get(f"{LIST}/pending", params={"q": q}, headers=owner).json()) == count
    before = client.get(f"{LIST}/pending", params={"before": "2026-10-05T10:00:02.000Z"}, headers=owner)
    assert [i["user"]["user"] for i in before.json()] == ["user00", "user01"]
    bad = client.get(f"{LIST}/pending", params={"after": "yesterday"}, headers=owner)
    assert bad.status_code == 400 and bad.headers["x-error-message"] == "* Invalid ISO datetime * at after"


@pytest.mark.parametrize(("body", "echo"), [
    ({"gated": "auto"}, {"gated": "auto"}),  # CFG-3 [OBS]
    ({"gatedNotificationsMode": "real-time"}, {}),  # CFG-7 [OBS]: stored, not echoed
    ({}, {}),  # CFG-3 [OBS]
    ({"gatedNotificationsEmail": "alerts@example.com", "gated": False, "private": False},
     {"private": False, "gated": False}),
])
def test_CFG_3_settings_echo_and_storage(client, store, body, echo):
    resp = client.put(f"/api/models/{REPO}/settings", json=body, headers=auth("owner"))
    assert (resp.status_code, resp.json()) == (200, echo)
    repo = store.repos[REPO]
    assert all(repo[k] == v for k, v in body.items())
    info = client.get(f"/api/models/{REPO}").json()
    assert "gatedNotificationsMode" not in info and "gatedNotificationsEmail" not in info  # CFG-3


def test_REV_6_grant_without_request_has_no_email(client):
    assert client.post(f"{LIST}/grant", json={"user": "DemoCarol"}, headers=auth("owner")).json() == {}
    (carol,) = [i for i in client.get(f"{LIST}/accepted", headers=auth("owner")).json()
                if i["user"]["user"] == "DemoCarol"]
    assert "email" not in carol["user"]  # REQ-5
    assert list(carol) == ["user", "timestamp", "reviewedAt", "status", "grantedBy"]  # REQ-6
    assert carol["grantedBy"]["user"] == "OwnerOfTheGatedModel"
    assert client.get(f"/api/models/{REPO}/auth-check", headers=auth("carol")).text == "OK"


def test_outbox_effects(client):
    """§7: manual new request → owner (or gatedNotificationsEmail); reset → requester + reason."""
    owner = auth("owner")
    client.put(f"/api/models/{REPO}/settings", json={"gatedNotificationsEmail": "alerts@example.com"}, headers=owner)
    client.post(f"/{REPO}/ask-access", json={}, headers=auth("carol"))
    client.post(f"{LIST}/handle", json={"user": "TestingBOrig", "status": "reset", "resetReason": "Re-read"},
                headers=owner)
    client.post(f"{LIST}/handle", json={"user": "DemoCarol", "status": "accepted"}, headers=owner)  # no e-mail (Q-20)
    client.post("/OwnerOfTheGatedModel/gated-auto-demo/ask-access", json={}, headers=auth("carol"))  # auto: no e-mail
    out = client.get("/__clone__/outbox").json()
    assert [(o["kind"], o["to"], o["user"], o.get("reason")) for o in out] == [
        ("new_request", "alerts@example.com", "DemoCarol", None),
        ("request_reset", "testingborig@example.com", "TestingBOrig", "Re-read"),
    ]
    assert out[0]["id"] != out[1]["id"] and len(out[0]["id"]) == 24


@pytest.mark.parametrize("encoding", ["json", "form"])
def test_REQ_2_ask_access_stores_form_answers(client, encoding):
    """REQ-2: JSON and form bodies behave the same; answers keyed by the card's field labels
    (gate-form.md). Provisional (Q-15/Q-16): values kept as sent, no required fields, unknown keys dropped."""
    answers = {"First Name": "Carol", "Country": "FR", "I accept the terms of the license": "on", "extra": "x"}
    kwargs = {"data": answers} if encoding == "form" else {"json": answers}
    resp = client.post("/OwnerOfTheGatedModel/gated-form-demo/ask-access", headers=auth("carol"), **kwargs)
    assert (resp.status_code, resp.headers["location"]) == (303, "http://127.0.0.1:8100/OwnerOfTheGatedModel/gated-form-demo")
    pending = "/api/models/OwnerOfTheGatedModel/gated-form-demo/user-access-request/pending"
    (item,) = client.get(pending, headers=auth("owner")).json()
    assert item["fields"] == {"First Name": "Carol", "Country": "FR", "I accept the terms of the license": "on"}


def test_auto_mode_accepts_immediately(client):
    client.post("/OwnerOfTheGatedModel/gated-auto-demo/ask-access", json={"I accept the above license agreement": "on"},
                headers=auth("carol"))
    assert client.get("/api/models/OwnerOfTheGatedModel/gated-auto-demo/auth-check", headers=auth("carol")).status_code == 200
    accepted = "/api/models/OwnerOfTheGatedModel/gated-auto-demo/user-access-request/accepted"
    (item,) = client.get(accepted, headers=auth("owner")).json()
    assert "grantedBy" not in item and item["reviewedAt"] == item["timestamp"]  # Provisional (Q-10)


def test_REQ_7_requester_self_cancel(client):
    """[OBS 2026-10-06 requester-cancel]: c2 (pending → deleted), c2-again/c3/c4 (404, no change), c6."""
    cancel = f"{LIST}/cancel"
    no_pending = (404, "No pending access request found for this repo and this user")
    ok = client.post(cancel, headers=auth("requester"))
    assert (ok.status_code, ok.json()) == (200, {"ok": True})
    msg = client.get(f"/api/models/{REPO}/auth-check", headers=auth("requester")).headers["x-error-message"]
    assert "not in the authorized list" in msg  # back to "no request"
    assert client.get(f"{LIST}/pending", headers=auth("owner")).json() == []
    again = client.post(cancel, headers=auth("requester"))
    assert (again.status_code, again.headers["x-error-message"]) == no_pending
    assert "x-error-code" not in again.headers
    # accepted (and rejected, reset): not withdrawable, unchanged
    client.post(f"/{REPO}/ask-access", json={}, headers=auth("requester"), follow_redirects=False)
    client.post(f"{LIST}/handle", json={"user": "TestingBOrig", "status": "accepted"}, headers=auth("owner"))
    refused = client.post(cancel, headers=auth("requester"))
    assert (refused.status_code, refused.headers["x-error-message"]) == no_pending
    assert [i["status"] for i in client.get(f"{LIST}/accepted", headers=auth("owner")).json()] == ["accepted"]
    assert client.post(cancel).status_code == 401


def test_CFG_4_private_repo_is_hidden_from_others(client):
    """Provisional (CFG-4): a private repo answers like a missing one, except to its owner."""
    client.put(f"/api/models/{REPO}/settings", json={"private": True}, headers=auth("owner"))
    assert client.get(f"/api/models/{REPO}").status_code == 401
    assert client.get(f"/api/models/{REPO}", headers=auth("requester")).headers["x-error-code"] == "RepoNotFound"
    assert client.get(f"/api/models/{REPO}", headers=auth("owner")).json()["private"] is True


def test_Q_25_quicksearch(client):
    """Provisional (Q-25): username/fullname prefix, case-insensitive; `type` must be `user` [OBS]."""
    users = client.get("/api/quicksearch", params={"q": "demo", "type": "user"}, headers=auth("owner")).json()
    assert users == {"users": [{"_id": users["users"][0]["_id"], "avatarUrl": users["users"][0]["avatarUrl"],
                                "fullname": "Carol Demo", "user": "DemoCarol"}]}
    assert client.get("/api/quicksearch", params={"q": "x", "type": "users"}).status_code == 400


def test_tree_synthesised_entries_are_consistent(client):
    """Files the fixtures do not describe get stub metadata whose oid matches the served bytes."""
    import hashlib

    # Every sandbox file is described by the fixtures; the clone-only demo repos are not.
    demo = "OwnerOfTheGatedModel/gated-form-demo"
    entries = client.get(f"/api/models/{demo}/tree/main").json()
    assert [e["path"] for e in entries] == ["README.md", "config.json", "model.safetensors"]
    config = next(e for e in entries if e["path"].endswith("config.json"))
    body = client.get(f"/{demo}/resolve/main/{config['path']}", headers=auth("owner"))
    assert hashlib.sha1(b"blob %d\x00" % len(body.content) + body.content).hexdigest() == config["oid"]
    assert body.headers["etag"] == f'"{config["oid"]}"' and int(body.headers["content-length"]) == config["size"]
    lfs = next(e for e in entries if "lfs" in e)
    assert lfs["lfs"]["oid"] == "*" * 64 and lfs["xetHash"] == "*" * 64  # masked on a gated repo


def test_CFG_6_not_gated_repo_redirects_to_resolve_cache(client):
    client.put(f"/api/models/{REPO}/settings", json={"gated": False}, headers=auth("owner"))
    resp = client.get(f"/{REPO}/resolve/main/README.md")
    assert resp.status_code == 307 and "etag" not in resp.headers
    cached = client.get(resp.headers["location"])
    sandbox = builtin_seed("sandbox")["repos"][0]  # [OBS 2026-10-06 clone-seed-reads owner-readme]
    assert cached.status_code == 200 and cached.text == sandbox["files"]["README.md"]["text"]
    assert cached.headers["x-repo-commit"] == sandbox["sha"]


@pytest.mark.parametrize(("setup", "persona", "repo", "masked"), [
    (None, None, REPO, True),  # ACC-9 [OBS tree-subdir-anon]
    (None, "requester", REPO, True),  # [OBS tree-subdir-requester]: pending, no access
    (None, "owner", REPO, False),  # [OBS tree-subdir-owner]: ACC-1
    ("accept", "requester", REPO, False),  # accepted request = access
    (None, None, "OwnerOfTheGatedModel/not-gated-demo", False),  # ACC-7: everyone has access
])
def test_ACC_9_tree_masks_lfs_hashes_without_access(client, setup, persona, repo, masked):
    if setup == "accept":
        client.post(f"{LIST}/handle", json={"user": "TestingBOrig", "status": "accepted"}, headers=auth("owner"))
    (lfs,) = [e for e in client.get(f"/api/models/{repo}/tree/main", params={"recursive": "true"},
                                    headers=auth(persona)).json() if "lfs" in e][:1]
    assert (lfs["lfs"]["oid"] == "*" * 64, lfs["xetHash"] == "*" * 64) == (masked, masked)
    assert len(lfs["oid"]) == 40 and lfs["oid"] != "*" * 40  # the git oid is never masked


def test_ACC_10_raw_serves_the_git_blob(client):
    """[OBS raw-readme-owner] README as text with resolve's headers. Provisional (no Q yet): an LFS
    file is served as its pointer, whose git oid is the recorded one."""
    lfs = client.get(f"/{REPO}/raw/main/checkpoint-0/model.safetensors", headers=auth("owner"))
    assert lfs.status_code == 200 and lfs.text.startswith("version https://git-lfs.github.com/spec/v1\n")
    # git oid and pointer size from the recorded tree [OBS 2026-10-06 clone-seed-reads tree-subdir]
    assert (lfs.headers["etag"], lfs.headers["content-length"]) == ('"73500655b76ca057265c754b218fbfab58751f0b"', "131")


def test_ACC_10_blob_page_ignores_the_token_and_allowlists_readme(client):
    path = f"/{REPO}/blob/main/checkpoint-0/config.json"
    anon = client.get(path)
    # [OBS anonymous-probes blob-config]: HTML, GatedRepo, and no WWW-Authenticate on this route
    assert (anon.status_code, anon.headers["x-error-code"], anon.headers["content-type"]) == (401, "GatedRepo", HTML)
    assert "www-authenticate" not in anon.headers and anon.headers["x-error-message"] == GATE_ANON
    # [OBS 2026-10-06 blob]: an HTML page ignores the Bearer token, even the owner's, and missing files
    # are gated too (ACC-6); README.md is allowlisted (ACC-5), anonymous or not.
    for persona in ("requester", "owner"):
        resp = client.get(path, headers=auth(persona))
        assert (resp.status_code, resp.headers["x-error-message"]) == (401, GATE_ANON)
    assert client.get(f"/{REPO}/blob/main/no-such-file.txt", headers=auth("owner")).status_code == 401
    readme = client.get(f"/{REPO}/blob/main/README.md")  # Provisional (no Q yet): minimal page
    assert readme.status_code == 200 and readme.headers["content-type"] == HTML
    assert "tiny-gated-model" in readme.text
    assert client.head(f"/{REPO}/blob/main/README.md").status_code == 200
