"""Exchange log and control endpoints."""

import json

import httpx
import pytest
from conftest import OTHER_REPO, OWNER_TOKEN, REPO, REQUESTER_TOKEN


def test_health_reports_config_without_secrets(make_bridge):
    client, upstream = make_bridge(tokens={"owner": OWNER_TOKEN})
    response = client.get("/__bridge__/health")
    assert response.json() == {
        "ok": True,
        "upstream": "https://huggingface.co",
        "public_url": "http://bridge.test",
        "repos": [REPO],
        "personas": {"owner": True, "requester": False},
    }
    assert OWNER_TOKEN not in response.text
    assert upstream.requests == [] and client.get("/__bridge__/log").json() == []  # control calls are not logged


def test_log_entries_cover_forwarded_and_rejected_calls(make_bridge):
    def respond(request):
        return httpx.Response(200, json={"echo": "ok"}, headers={"X-Total-Count": "1", "Set-Cookie": "a=b"})

    client, _ = make_bridge(respond)
    owner = {"Authorization": "Bearer persona-owner"}
    client.put(f"/api/models/{REPO}/settings", json={"gated": "manual"}, headers=owner)
    client.post(
        f"/{REPO}/ask-access",
        content=b"Affiliation=ACME+Corp",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    client.get(f"/api/models/{OTHER_REPO}", headers=owner)  # repo rejected
    client.get("/nope")  # route rejected

    entries = client.get("/__bridge__/log").json()
    assert [e["id"] for e in entries] == [1, 2, 3, 4]
    put, ask, repo_rejected, route_rejected = entries
    assert put["persona"] == "owner" and put["method"] == "PUT"
    assert put["path"] == f"/api/models/{REPO}/settings" and put["query"] == ""
    assert put["request_body"] == {"gated": "manual"}
    assert put["status"] == 200 and put["upstream"] is True
    assert put["response_body"] == {"echo": "ok"}
    assert put["response_headers"] == {"Content-Type": "application/json", "X-Total-Count": "1"}
    assert put["started_at"].endswith("Z") and len(put["started_at"]) == len("2026-10-05T12:00:00.000Z")
    assert put["duration_ms"] >= 0
    assert ask["persona"] == "anonymous" and ask["request_body"] == {"Affiliation": "ACME Corp"}
    assert (repo_rejected["status"], repo_rejected["upstream"]) == (403, False)
    assert repo_rejected["response_headers"]["X-Error-Code"] == "BridgeRepoNotAllowed"
    assert (route_rejected["status"], route_rejected["upstream"]) == (404, False)
    assert route_rejected["response_headers"]["X-Error-Code"] == "BridgeRouteNotAllowed"


def test_log_limit_newest_last_and_delete(bridge):
    client, _ = bridge
    for _ in range(5):
        client.get("/api/whoami-v2")
    assert [e["id"] for e in client.get("/__bridge__/log?limit=2").json()] == [4, 5]
    assert len(client.get("/__bridge__/log").json()) == 5

    assert client.delete("/__bridge__/log").json() == {"cleared": 5}
    assert client.get("/__bridge__/log").json() == []
    client.get("/api/whoami-v2")
    assert [e["id"] for e in client.get("/__bridge__/log").json()] == [6]  # ids stay unique across clears


def test_jsonl_file_is_appended_and_survives_clear(make_bridge, tmp_path):
    client, _ = make_bridge()
    client.get("/api/whoami-v2")
    client.delete("/__bridge__/log")
    client.get("/api/whoami-v2")
    lines = [json.loads(line) for line in (tmp_path / "bridge.jsonl").read_text().splitlines()]
    assert [line["id"] for line in lines] == [1, 2]


def test_log_file_can_be_disabled(make_bridge, tmp_path):
    client, _ = make_bridge(log_file=None)
    client.get("/api/whoami-v2")
    assert not (tmp_path / "bridge.jsonl").exists()
    assert len(client.get("/__bridge__/log").json()) == 1


@pytest.mark.parametrize(
    ("content_type", "body", "expected"),
    [
        ("text/plain; charset=utf-8", b"x" * 5000, "x" * 2000 + "…"),
        ("text/markdown", "héllo".encode(), "héllo"),
        ("application/octet-stream", b"\x00" * 123, {"bytes": 123}),
        ("application/json", b'["a", {"b": 1}]', ["a", {"b": 1}]),
        ("application/json", b"not json", "not json"),
        ("text/plain", b"", None),
    ],
    ids=["long-text", "short-text", "binary", "json", "bad-json", "empty"],
)
def test_response_body_summary(make_bridge, content_type, body, expected):
    client, _ = make_bridge(lambda request: httpx.Response(200, content=body, headers={"Content-Type": content_type}))
    client.get(f"/{REPO}/resolve/main/f")
    (entry,) = client.get("/__bridge__/log").json()
    assert entry["response_body"] == expected


def test_request_body_strings_are_truncated(bridge):
    client, _ = bridge
    client.post(f"/{REPO}/ask-access", json={"reason": "y" * 5000, "nested": ["z" * 3000]})
    (entry,) = client.get("/__bridge__/log").json()
    assert entry["request_body"] == {"reason": "y" * 2000 + "…", "nested": ["z" * 2000 + "…"]}


def test_tokens_are_redacted_even_if_upstream_echoes_them(make_bridge, tmp_path):
    def echo(request):
        return httpx.Response(200, json={"seen": request.headers["authorization"]})

    client, _ = make_bridge(echo)
    for persona in ("owner", "requester"):
        client.get("/api/whoami-v2", headers={"Authorization": f"Bearer persona-{persona}"})
    logged = json.dumps(client.get("/__bridge__/log").json()) + (tmp_path / "bridge.jsonl").read_text()
    assert OWNER_TOKEN not in logged and REQUESTER_TOKEN not in logged
    assert "authorization" not in logged.lower().replace("invalid credentials in authorization header", "")
