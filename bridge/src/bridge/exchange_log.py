"""Exchange log: every call the bridge receives, kept in memory and appended to a JSONL file.

Real tokens are never logged: the Authorization header is not recorded, and any token value that
turns up in a body is replaced by `<redacted>`.
"""

from __future__ import annotations

import itertools
import json
from collections import deque
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

MAX_ENTRIES = 1000
MAX_STRING = 2000
MAX_JSON_BYTES = 256_000  # bigger JSON bodies are logged as {"bytes": n}
MAX_TEXT_SCAN = 64_000  # bytes decoded for a text excerpt

TEXT_TYPES = ("text/", "application/xml")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").removesuffix("+00:00") + "Z"


def _media_type(content_type: str | None) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def _is_json(media_type: str) -> bool:
    return media_type == "application/json" or media_type.endswith("+json")


class ExchangeLog:
    def __init__(self, path: Path | None, secrets: Iterable[str] = ()):
        self._entries: deque[dict[str, Any]] = deque(maxlen=MAX_ENTRIES)
        self._ids = itertools.count(1)
        self._path = path
        self._secrets = [s for s in secrets if s]
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, **fields: Any) -> dict[str, Any]:
        entry = {"id": next(self._ids), **fields}
        entry = self._clean(entry)
        self._entries.append(entry)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def entries(self, limit: int) -> list[dict[str, Any]]:
        """The `limit` most recent entries, newest last."""
        return list(self._entries)[-limit:]

    def clear(self) -> int:
        """Empty the in-memory log. The JSONL file is an append-only audit trail and is kept."""
        count = len(self._entries)
        self._entries.clear()
        return count

    def _clean(self, value: Any) -> Any:
        if isinstance(value, str):
            for secret in self._secrets:
                value = value.replace(secret, "<redacted>")
            return value if len(value) <= MAX_STRING else value[:MAX_STRING] + "…"
        if isinstance(value, dict):
            return {k: self._clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._clean(v) for v in value]
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
    except ValueError:  # malformed body: log it as opaque rather than lose the entry
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
