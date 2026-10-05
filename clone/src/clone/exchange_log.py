"""Exchange-log entry helpers, with the same entry schema and body summaries as the bridge's
`/__bridge__/log` (bridge/src/bridge/exchange_log.py), so `harness/kb/bridge_log_to_md.py` and
diffs work on both backends (docs/system.md "Control endpoints").
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

MAX_STRING = 2000
MAX_JSON_BYTES = 256_000
MAX_TEXT_SCAN = 64_000
TEXT_TYPES = ("text/", "application/xml")

# docs/system.md "Backend surface": the response headers both backends keep (and log).
RESPONSE_HEADERS = (
    "Content-Type", "Content-Disposition", "X-Error-Code", "X-Error-Message", "WWW-Authenticate",
    "Link", "Location", "X-Total-Count", "X-Repo-Commit", "ETag",
)


def _media_type(content_type: str | None) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def _is_json(media_type: str) -> bool:
    return media_type == "application/json" or media_type.endswith("+json")


def clean(value: Any) -> Any:
    """Long strings are cut like the bridge does."""
    if isinstance(value, str):
        return value if len(value) <= MAX_STRING else value[:MAX_STRING] + "…"
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def summarize_request_body(content_type: str | None, body: bytes) -> Any:
    """Parsed JSON or form, None when empty, else {"bytes": n}."""
    if not body:
        return None
    media_type = _media_type(content_type)
    try:
        if _is_json(media_type):
            return json.loads(body)
        if media_type == "application/x-www-form-urlencoded":
            form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
            return {k: v[0] if len(v) == 1 else v for k, v in form.items()}
    except ValueError:
        pass
    return {"bytes": len(body)}


def summarize_response_body(content_type: str | None, body: bytes) -> Any:
    """Parsed JSON if JSON, a text excerpt for text, None when empty, else {"bytes": n}."""
    if not body:
        return None
    media_type = _media_type(content_type)
    if _is_json(media_type):
        if len(body) > MAX_JSON_BYTES:
            return {"bytes": len(body)}
        try:
            return json.loads(body)
        except ValueError:
            pass
    elif not media_type.startswith(TEXT_TYPES):
        return {"bytes": len(body)}
    return body[:MAX_TEXT_SCAN].decode("utf-8", errors="replace")
