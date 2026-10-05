"""Pure helpers for the proxy: persona mapping, response header filtering, URL rewriting."""

from __future__ import annotations

import re
from collections.abc import Iterable

USER_AGENT = "originator-bridge/0.1"

# docs/system.md "Backend surface": the only upstream response headers that pass through.
# `Set-Cookie` is deliberately absent.
RESPONSE_HEADERS = (
    "Content-Type",
    "Content-Disposition",
    "X-Error-Code",
    "X-Error-Message",
    "WWW-Authenticate",
    "Link",
    "Location",
    "X-Total-Count",
    "X-Repo-Commit",
    "ETag",
)
# The only request headers forwarded besides the persona's Authorization.
REQUEST_HEADERS = ("content-type", "accept")

# docs/system.md "Personas": fake token sent by the web app -> persona.
FAKE_TOKENS = {"persona-owner": "owner", "persona-requester": "requester"}

INVALID_CREDENTIALS = "Invalid credentials in Authorization header"


def identify_persona(authorization: str | None) -> str | None:
    """`anonymous` without header, `owner`/`requester` for a fake token, None for anything else."""
    if authorization is None:
        return "anonymous"
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer":
        return FAKE_TOKENS.get(value.strip())
    return None


def rewrite_location(value: str, upstream: str, public_url: str) -> str:
    """Rewrite an absolute upstream URL to the bridge's public URL; relative and foreign URLs stay."""
    return re.sub(rf"^{re.escape(upstream)}(?=[/?#]|$)", public_url, value)


def rewrite_link(value: str, upstream: str, public_url: str) -> str:
    """Rewrite upstream URLs in the `<url>` targets of a Link header (pagination `rel="next"`)."""
    return re.sub(rf"(?<=<){re.escape(upstream)}(?=[/?#>])", public_url, value)


def filter_response_headers(
    raw_headers: Iterable[tuple[bytes, bytes]], upstream: str, public_url: str
) -> dict[str, str]:
    """Keep the allowed headers (repeated ones are comma-joined) with Location/Link rewritten.

    Values are decoded as latin-1, which round-trips the bytes exactly when Starlette re-encodes them.
    """
    raw = [(k.decode("latin-1").lower(), v.decode("latin-1")) for k, v in raw_headers]
    kept: dict[str, str] = {}
    for name in RESPONSE_HEADERS:
        values = [v for k, v in raw if k == name.lower()]
        if not values:
            continue
        value = ", ".join(values)
        if name == "Location":
            value = rewrite_location(value, upstream, public_url)
        elif name == "Link":
            value = rewrite_link(value, upstream, public_url)
        kept[name] = value
    return kept
