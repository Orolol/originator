"""Thin helper over the backend under test: HF routes as personas + the clone's control endpoints.

Control endpoints are the documented clone contract (docs/system.md, "Clone (Python, :8200): contract"),
used as a black box.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .replay import make_client, send, to_actual


class Backend:
    def __init__(self, base_url: str | None = None):
        self.client = make_client(base_url)
        self.base_url = str(self.client.base_url).rstrip("/")

    def close(self) -> None:
        self.client.close()

    # HF surface -----------------------------------------------------------------------------
    def req(self, persona: str, method: str, path: str, body: Any = None, encoding: str | None = None,
            headers: dict | None = None) -> httpx.Response:
        return send(self.client, persona, method, path, body, encoding, headers)

    def get(self, persona: str, path: str) -> httpx.Response:
        return self.req(persona, "GET", path)

    def list_requests(self, repo: str, status: str, query: str = "", persona: str = "owner") -> httpx.Response:
        return self.get(persona, f"/api/models/{repo}/user-access-request/{status}{query}")

    def handle(self, repo: str, body: dict, persona: str = "owner") -> httpx.Response:
        return self.req(persona, "POST", f"/api/models/{repo}/user-access-request/handle", body)

    def grant(self, repo: str, body: dict, persona: str = "owner") -> httpx.Response:
        return self.req(persona, "POST", f"/api/models/{repo}/user-access-request/grant", body)

    def batch(self, repo: str, body: dict, persona: str = "owner") -> httpx.Response:
        return self.req(persona, "POST", f"/api/models/{repo}/user-access-request/batch", body)

    def ask(self, repo: str, persona: str = "requester", body: Any = None, encoding: str = "json") -> httpx.Response:
        return self.req(persona, "POST", f"/{repo}/ask-access", {} if body is None else body, encoding)

    def settings(self, repo: str, body: dict, persona: str = "owner") -> httpx.Response:
        return self.req(persona, "PUT", f"/api/models/{repo}/settings", body)

    def auth_check(self, repo: str, persona: str) -> httpx.Response:
        return self.get(persona, f"/api/models/{repo}/auth-check")

    def resolve(self, repo: str, path: str, persona: str, rev: str = "main", method: str = "GET") -> httpx.Response:
        return self.req(persona, method, f"/{repo}/resolve/{rev}/{path}")

    def report(self, repo: str, persona: str = "owner") -> httpx.Response:
        return self.get(persona, f"/{repo}/user-access-report")

    # control endpoints (clone only) ------------------------------------------------------------
    def _control(self, method: str, path: str, body: Any = None) -> httpx.Response:
        kwargs = {} if body is None else {"content": json.dumps(body).encode(),
                                           "headers": {"Content-Type": "application/json"}}
        response = self.client.request(method, f"{self.base_url}/__clone__/{path}", **kwargs)
        return response

    def health(self) -> dict:
        return self._ok(self._control("GET", "health"))

    def reset(self, seed: str | None = None) -> httpx.Response:
        return self._control("POST", "reset", None if seed is None else {"seed": seed})

    def state(self) -> dict:
        return self._ok(self._control("GET", "state"))

    def put_state(self, document: dict) -> httpx.Response:
        response = self._control("PUT", "state", document)
        if response.status_code >= 300:
            raise AssertionError(f"PUT /__clone__/state -> {response.status_code}: {response.text[:800]}")
        return response

    def clock(self) -> dict:
        return self._ok(self._control("GET", "clock"))

    def set_clock(self, body: dict) -> httpx.Response:
        return self._control("POST", "clock", body)

    def outbox(self) -> list[dict]:
        return self._ok(self._control("GET", "outbox"))

    def clear_outbox(self) -> httpx.Response:
        return self._control("DELETE", "outbox")

    def log(self) -> list[dict]:
        return self._ok(self._control("GET", "log"))

    def clear_log(self) -> httpx.Response:
        return self._control("DELETE", "log")

    @staticmethod
    def _ok(response: httpx.Response) -> Any:
        if response.status_code >= 300:
            raise AssertionError(f"{response.request.method} {response.request.url} -> {response.status_code}: "
                                 f"{response.text[:500]}")
        return response.json()


def snapshot(response: httpx.Response) -> dict:
    """Everything observable about a response, for determinism comparisons."""
    actual = to_actual(response)
    return {"status": actual.status, "headers": sorted(actual.headers.items()), "body": actual.body.decode("utf-8", "replace")}
