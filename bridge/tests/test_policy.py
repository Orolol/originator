"""What the bridge lets through: route allowlist, repo allowlist, persona auth (docs/system.md)."""

import json

import httpx
import pytest
from conftest import OTHER_REPO, OWNER_TOKEN, REPO, REQUESTER_TOKEN

R = REPO

# Every row of the "Backend surface" table (with `{repo}` filled in).
ALLOWED = [
    ("GET", "/api/whoami-v2"),
    ("GET", "/api/quicksearch?q=ori&type=user"),
    ("GET", f"/api/models/{R}"),
    ("GET", f"/api/models/{R}/tree/main"),
    ("GET", f"/api/models/{R}/tree/main/sub/dir"),
    ("GET", f"/api/models/{R}/auth-check"),
    ("PUT", f"/api/models/{R}/settings"),
    ("GET", f"/api/models/{R}/user-access-request/pending"),
    ("GET", f"/api/models/{R}/user-access-request/accepted"),
    ("GET", f"/api/models/{R}/user-access-request/rejected"),
    ("GET", f"/api/models/{R}/user-access-request/reset"),
    ("POST", f"/api/models/{R}/user-access-request/handle"),
    ("POST", f"/api/models/{R}/user-access-request/grant"),
    ("POST", f"/api/models/{R}/user-access-request/batch"),
    ("POST", f"/api/models/{R}/user-access-request/cancel"),
    ("POST", f"/{R}/ask-access"),
    ("GET", f"/{R}/user-access-report"),
    ("GET", f"/{R}/resolve/main/README.md"),
    ("HEAD", f"/{R}/resolve/main/README.md"),
    ("GET", f"/{R}/resolve/main/sub/dir/weights.bin"),
    ("GET", f"/{R}/resolve/refs%2Fpr%2F1/README.md"),
]


@pytest.mark.parametrize(("method", "target"), ALLOWED)
def test_allowed_routes_are_forwarded_unchanged(bridge, method, target):
    client, upstream = bridge
    assert client.request(method, target).status_code == 200
    (sent,) = upstream.requests
    assert sent.method == method
    assert sent.url.raw_path.decode() == target
    assert sent.url.host == "huggingface.co"


@pytest.mark.parametrize(
    ("method", "target"),
    [
        ("DELETE", f"/api/models/{R}"),
        ("PUT", f"/api/models/{R}"),
        ("GET", f"/api/models/{R}/discussions"),
        ("GET", f"/api/models/{R}/settings"),
        ("POST", f"/api/models/{R}/settings"),
        ("GET", f"/api/models/{R}/user-access-request/everything"),
        ("POST", f"/api/models/{R}/user-access-request/pending"),
        ("GET", f"/api/models/{R}/user-access-request/handle"),
        ("POST", f"/api/models/{R}/resolve/main/f"),
        ("GET", f"/{R}"),  # the HTML model page is not part of the surface
        ("GET", f"/{R}/ask-access"),
        ("POST", f"/{R}/resolve/main/README.md"),
        ("GET", f"/{R}/resolve/main"),
        ("GET", f"/{R}/raw/main/README.md"),
        ("GET", "/api/models"),
        ("GET", "/api/whoami-v2/extra"),
        ("POST", "/api/whoami-v2"),
        ("POST", "/api/models/ask-access"),  # `api` is no namespace: not a repo-scoped web route
        ("GET", "/api/models/resolve/main/f"),
        ("GET", f"/{R}/resolve/main/../../../{OTHER_REPO}/resolve/main/f"),  # dot segments escape the repo
        ("GET", f"/{R}/resolve/main/%2e%2e/%2e%2e/x/y"),
        ("GET", "/"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("GET", "/__bridge__/unknown"),
        ("PATCH", f"/api/models/{R}/settings"),
        ("OPTIONS", "/api/whoami-v2"),
        ("TRACE", "/api/whoami-v2"),
    ],
)
def test_route_allowlist_rejects_everything_else(bridge, method, target):
    client, upstream = bridge
    response = client.request(method, target)
    assert response.status_code == 404
    assert response.headers["x-error-code"] == "BridgeRouteNotAllowed"
    assert response.json()["error"].startswith("Route not allowed by bridge")
    assert upstream.requests == []


@pytest.mark.parametrize(
    ("method", "template"),
    [(m, t) for m, t in ALLOWED if "/api/whoami" not in t and "quicksearch" not in t],
)
def test_repo_allowlist(bridge, method, template):
    client, upstream = bridge
    response = client.request(method, template.replace(REPO, OTHER_REPO))
    assert response.status_code == 403
    assert response.headers["x-error-code"] == "BridgeRepoNotAllowed"
    if method != "HEAD":
        assert response.json() == {"error": f"Repo not allowed by bridge: {OTHER_REPO}"}
    assert upstream.requests == []


def test_repo_allowlist_is_configurable(make_bridge):
    client, upstream = make_bridge(repos=(REPO, OTHER_REPO))
    assert client.get(f"/api/models/{OTHER_REPO}").status_code == 200
    assert len(upstream.requests) == 1


@pytest.mark.parametrize(
    ("authorization", "expected_upstream_authorization"),
    [
        (None, None),
        ("Bearer persona-owner", f"Bearer {OWNER_TOKEN}"),
        ("bearer persona-requester", f"Bearer {REQUESTER_TOKEN}"),
    ],
    ids=["anonymous", "owner", "requester"],
)
def test_persona_token_mapping(bridge, authorization, expected_upstream_authorization):
    client, upstream = bridge
    headers = {"Authorization": authorization} if authorization else {}
    response = client.get("/api/whoami-v2", headers=headers)
    assert response.status_code == 200
    assert upstream.requests[0].headers.get("authorization") == expected_upstream_authorization
    # real tokens never come back to the caller nor reach the log
    everything = response.text + str(dict(response.headers)) + json.dumps(client.get("/__bridge__/log").json())
    assert OWNER_TOKEN not in everything
    assert REQUESTER_TOKEN not in everything


@pytest.mark.parametrize(
    "authorization",
    [
        f"Bearer {OWNER_TOKEN}",
        "Bearer persona-admin",
        "Bearer",
        "Bearer ",
        "persona-owner",
        "Basic cGVyc29uYTpvd25lcg==",
        "",
    ],
)
def test_unknown_authorization_is_401_without_upstream_call(bridge, authorization):
    client, upstream = bridge
    response = client.get("/api/whoami-v2", headers={"Authorization": authorization})
    message = "Invalid username or password."  # HF's wording for an invalid token [OBS]
    assert response.status_code == 401
    assert response.json() == {"error": message}
    assert response.headers["x-error-message"] == message
    assert response.headers["www-authenticate"] == 'Bearer realm="Authentication required", charset="UTF-8"'
    assert upstream.requests == []
    (entry,) = client.get("/__bridge__/log").json()
    assert (entry["persona"], entry["upstream"], entry["status"]) == ("invalid", False, 401)
    # The credential must not be logged anywhere; the logged WWW-Authenticate response header
    # legitimately contains "Bearer", so it is excluded from the search.
    logged = json.dumps({k: v for k, v in entry.items() if k != "response_headers"})
    assert authorization.strip() == "" or authorization not in logged


def test_unconfigured_persona_fails_instead_of_going_anonymous(make_bridge):
    client, upstream = make_bridge(tokens={"requester": REQUESTER_TOKEN})
    response = client.get("/api/whoami-v2", headers={"Authorization": "Bearer persona-owner"})
    assert response.status_code == 503
    assert response.headers["x-error-code"] == "BridgePersonaNotConfigured"
    assert upstream.requests == []


@pytest.mark.parametrize(
    ("exception", "status", "code"),
    [
        (httpx.ReadTimeout("timed out"), 504, "BridgeUpstreamTimeout"),
        (httpx.ConnectError("refused for https://huggingface.co/x?token=secret"), 502, "BridgeUpstreamError"),
    ],
)
def test_upstream_failure_is_reported_not_retried(make_bridge, exception, status, code):
    def fail(request):
        raise exception

    client, upstream = make_bridge(fail)
    response = client.get("/api/whoami-v2", headers={"Authorization": "Bearer persona-owner"})
    assert (response.status_code, response.headers["x-error-code"]) == (status, code)
    assert "secret" not in response.text
    assert len(upstream.requests) == 1
    (entry,) = client.get("/__bridge__/log").json()
    assert entry["upstream"] is True
