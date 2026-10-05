"""HF's exact texts (docs/hf-gated/api.md §3, behaviour.md §2) and assertion helpers for rule tests."""

from __future__ import annotations

import re

import httpx

INVALID_CREDENTIALS = "Invalid username or password."  # api.md §3.2-3.3, system.md Personas
WWW_AUTHENTICATE = 'Bearer realm="Authentication required", charset="UTF-8"'
NO_PERMISSION = "You have read access but not the required permissions for this operation"  # REV-12
NO_REQUEST = "No access request found matching your criteria"  # REV-1
USER_NOT_FOUND = "User not found"  # REV-12
ALREADY_HAS_ACCESS = "That user already has access to the repo"  # REV-7
REPO_NOT_FOUND = "Repository not found"  # api.md check order
ENTRY_NOT_FOUND = "Entry not found"  # ACC-6
NOT_FOUND_PAGE = "Sorry, we can't find the page you are looking for."  # owner-reads owner-get-settings


def gate_anonymous(repo: str) -> str:
    return (f"Access to model {repo} is restricted. You must have access to it and be authenticated to access it. "
            "Please log in.")


def gate_no_request(repo: str) -> str:
    return (f"Access to model {repo} is restricted and you are not in the authorized list. "
            f"Visit https://huggingface.co/{repo} to ask for access.")


def gate_pending(repo: str) -> str:
    return f"Your request to access model {repo} is awaiting a review from the repo authors."


def gate_rejected(repo: str) -> str:
    return f"Your request to access model {repo} has been rejected by the repo's authors."


def gate_reset(repo: str) -> str:
    return (f"Your request to access model {repo} has been reset by the repo's authors. "
            f"Visit https://huggingface.co/{repo} to submit a new request.")


def zod(message: str, path: str | None = None) -> str:
    """JSON `error` text of a validation failure (api.md "Validation message format")."""
    return f"✖ {message}" + (f"\n  → at {path}" if path else "")


def ascii_header(text: str) -> str:
    """X-Error-Message is an ASCII-sanitised copy: non-ASCII -> '*', whitespace runs -> one space."""
    return re.sub(r"\s+", " ", "".join(ch if ord(ch) < 128 else "*" for ch in text)).strip()


def media(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").split(";")[0].strip().lower()


def describe(response: httpx.Response) -> str:
    keep = ("content-type", "x-error-code", "x-error-message", "location", "www-authenticate", "link")
    headers = {k: v for k, v in response.headers.items() if k.lower() in keep}
    return f"{response.request.method} {response.request.url} -> {response.status_code} {headers} {response.text[:300]!r}"


def assert_error(response: httpx.Response, status: int, message: str, *, code: str | None = None,
                 body: str = "json", www_authenticate: bool | None = None) -> None:
    """Status, X-Error-Code (exact, or absent when None), X-Error-Message, and the body form.

    body="json": `{"error": message}` (API routes); "text": the message as text/plain (resolve);
    "zod": JSON error is `message`, header is its ASCII copy; "any": body not checked.
    """
    info = describe(response)
    assert response.status_code == status, info
    assert response.headers.get("x-error-code") == code, info
    if body == "zod":
        assert response.json() == {"error": message}, info
        assert response.headers.get("x-error-message") == ascii_header(message), info
    else:
        assert response.headers.get("x-error-message") == message, info
    if body == "json":
        assert media(response) == "application/json", info
        assert response.json() == {"error": message}, info
    elif body == "text":
        assert media(response) == "text/plain", info
        if response.request.method != "HEAD":
            assert response.text == message, info
    if www_authenticate is True:
        assert response.headers.get("www-authenticate") == WWW_AUTHENTICATE, info
    elif www_authenticate is False:
        assert "www-authenticate" not in response.headers, info


def assert_ok(response: httpx.Response, status: int = 200) -> None:
    info = describe(response)
    assert response.status_code == status, info
    assert "x-error-code" not in response.headers, info
    assert "x-error-message" not in response.headers, info
