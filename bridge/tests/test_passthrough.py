"""Fidelity of what is forwarded and returned: request shaping, response headers, URL rewriting."""

import httpx
import pytest
from conftest import PUBLIC_URL, REPO

from bridge.proxy import filter_response_headers

HUB = "https://huggingface.co"


def test_only_expected_request_headers_are_forwarded(bridge):
    client, upstream = bridge
    client.get(
        f"/api/models/{REPO}",
        headers={
            "Authorization": "Bearer persona-owner",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": "token=browser-session",
            "Referer": "http://localhost:3000/x",
            "Origin": "http://localhost:3000",
            "X-Forwarded-For": "10.0.0.1",
        },
    )
    sent = upstream.requests[0].headers
    assert sent["accept"] == "application/json"
    assert sent["content-type"] == "application/json"
    assert sent["user-agent"] == "originator-bridge/0.1"
    for header in ("cookie", "referer", "origin", "x-forwarded-for"):
        assert header not in sent


@pytest.mark.parametrize(
    "target",
    [
        f"/api/models/{REPO}?expand[]=gated&expand[]=cardData",
        f"/api/models/{REPO}/user-access-request/pending?limit=10&after=2026-10-05T13%3A31%3A55.250Z&q=a%20b",
        f"/api/models/{REPO}/tree/refs%2Fpr%2F1?recursive=true",
        f"/{REPO}/resolve/main/dir/a%20b.txt?download=true",
    ],
)
def test_path_and_query_are_forwarded_verbatim(bridge, target):
    client, upstream = bridge
    client.get(target)
    assert upstream.requests[0].url.raw_path.decode() == target


@pytest.mark.parametrize(
    ("method", "path", "content_type", "body"),
    [
        ("PUT", f"/api/models/{REPO}/settings", "application/json", b'{"gated":"manual","private":false}'),
        (
            "POST",
            f"/api/models/{REPO}/user-access-request/handle",
            "application/json",
            b'{"user":"TestingBOrig","status":"accepted"}',
        ),
        ("POST", f"/{REPO}/ask-access", "application/json", b'{"Affiliation":"ACME"}'),
        ("POST", f"/{REPO}/ask-access", "application/x-www-form-urlencoded", b"Affiliation=ACME+Corp&Country=FR"),
        ("POST", f"/api/models/{REPO}/user-access-request/cancel", None, b""),
    ],
    ids=["settings-json", "handle-json", "ask-access-json", "ask-access-form", "cancel-empty"],
)
def test_body_and_content_type_are_forwarded(bridge, method, path, content_type, body):
    client, upstream = bridge
    client.request(method, path, content=body, headers={"Content-Type": content_type} if content_type else {})
    (sent,) = upstream.requests
    assert sent.read() == body
    assert sent.headers.get("content-type") == content_type


STATUS_CASES = [
    (200, b'{"name":"Orosius"}', "application/json"),
    (401, b"Access to model x is restricted.", "text/plain; charset=utf-8"),
    (403, b'{"error":"nope"}', "application/json; charset=utf-8"),
    (404, b"", "text/plain"),
    (500, b"\x00\xff binary \x80", "application/octet-stream"),
]


@pytest.mark.parametrize(("status", "body", "content_type"), STATUS_CASES)
def test_status_body_and_allowed_headers_pass_through(make_bridge, status, body, content_type):
    allowed = {
        "X-Error-Code": "GatedRepo",
        "X-Error-Message": "Access to model x is restricted and you are not in the authorized list.",
        "WWW-Authenticate": 'Bearer realm="Authentication required", charset="UTF-8"',
        "Content-Disposition": 'attachment; filename="user-access-report.csv"',
        "X-Total-Count": "42",
        "X-Repo-Commit": "a" * 40,
        "ETag": '"abc123"',
    }
    dropped = {
        "Set-Cookie": "hf-chat=1; Path=/; HttpOnly",
        "X-Request-Id": "Root=1-abc",
        "Access-Control-Expose-Headers": "X-Error-Code",
        "Server": "hf",
        "Content-Encoding": "identity",
    }
    client, _ = make_bridge(
        lambda request: httpx.Response(
            status, content=body, headers={"Content-Type": content_type, **allowed, **dropped}
        )
    )
    response = client.get(f"/api/models/{REPO}/auth-check")
    assert response.status_code == status
    assert response.content == body
    assert response.headers["content-type"] == content_type
    for name, value in allowed.items():
        assert response.headers[name] == value
    for name in ("set-cookie", "x-request-id", "access-control-expose-headers", "server", "content-encoding"):
        assert name not in response.headers


def test_non_ascii_header_bytes_survive():
    # Unit-level: Starlette's TestClient cannot represent such headers, but the bytes must round-trip.
    raw = "Access to model “x” is restricted".encode()
    kept = filter_response_headers([(b"X-Error-Message", raw), (b"Set-Cookie", b"a=b")], HUB, PUBLIC_URL)
    assert kept == {"X-Error-Message": raw.decode("latin-1")}
    assert kept["X-Error-Message"].encode("latin-1") == raw


def test_upstream_cookies_are_never_replayed(make_bridge):
    def respond(request):
        return httpx.Response(200, headers={"Set-Cookie": "session=persona-owner-session; Path=/"})

    client, upstream = make_bridge(respond)
    first = client.get("/api/whoami-v2", headers={"Authorization": "Bearer persona-owner"})
    client.get("/api/whoami-v2", headers={"Authorization": "Bearer persona-requester"})
    assert "set-cookie" not in first.headers
    assert all("cookie" not in request.headers for request in upstream.requests)


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (f"{HUB}/{REPO}", f"{PUBLIC_URL}/{REPO}"),
        (f"{HUB}/{REPO}?x=1#frag", f"{PUBLIC_URL}/{REPO}?x=1#frag"),
        (HUB, PUBLIC_URL),
        (f"/{REPO}", f"/{REPO}"),
        (
            "https://cas-bridge.xethub.hf.co/xet-bridge-us/abc?X-Amz-Signature=1",
            "https://cas-bridge.xethub.hf.co/xet-bridge-us/abc?X-Amz-Signature=1",
        ),
        ("https://huggingface.co.evil.example/x", "https://huggingface.co.evil.example/x"),
        (f"https://example.org/?next={HUB}/x", f"https://example.org/?next={HUB}/x"),
    ],
    ids=["absolute", "query-fragment", "origin-only", "relative", "cdn", "lookalike-host", "url-in-query"],
)
def test_location_rewrite_on_ask_access_303(make_bridge, location, expected):
    client, upstream = make_bridge(lambda request: httpx.Response(303, headers={"Location": location}))
    response = client.post(f"/{REPO}/ask-access", json={})
    assert response.status_code == 303  # not followed
    assert response.headers["location"] == expected
    assert len(upstream.requests) == 1


def test_cdn_redirect_on_resolve_is_returned_not_followed(make_bridge):
    cdn = "https://cas-bridge.xethub.hf.co/file?sig=1"
    client, upstream = make_bridge(lambda request: httpx.Response(302, headers={"Location": cdn, "ETag": '"e"'}))
    response = client.get(f"/{REPO}/resolve/main/model.safetensors")
    assert (response.status_code, response.headers["location"]) == (302, cdn)
    assert len(upstream.requests) == 1


def test_link_header_pagination_is_rewritten(make_bridge):
    next_url = f"{HUB}/api/models/{REPO}/user-access-request/pending?limit=1&after=2026-10-05T13%3A31%3A55.250Z"
    link = f'<{next_url}>; rel="next", <https://cdn.example/other>; rel="alternate"'
    client, _ = make_bridge(lambda request: httpx.Response(200, json=[], headers={"Link": link}))
    response = client.get(f"/api/models/{REPO}/user-access-request/pending?limit=1")
    assert response.headers["link"] == (
        f'<{PUBLIC_URL}{next_url.removeprefix(HUB)}>; rel="next", <https://cdn.example/other>; rel="alternate"'
    )


def test_head_on_resolve(make_bridge):
    headers = {"ETag": '"e"', "X-Repo-Commit": "b" * 40, "Content-Type": "text/plain", "Content-Length": "1234"}
    client, upstream = make_bridge(lambda request: httpx.Response(200, headers=headers))
    response = client.head(f"/{REPO}/resolve/main/README.md")
    assert upstream.requests[0].method == "HEAD"
    assert response.status_code == 200
    assert response.headers["etag"] == '"e"'
    assert response.headers["x-repo-commit"] == "b" * 40
    assert response.content == b""
