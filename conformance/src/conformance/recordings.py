"""Load real-Hub recordings into one replayable step model.

Two formats exist under docs/hf-gated/observations/:

- probe format (`harness/kb/probe.py`): `{"_meta", "records": [{id, as, method, url, request_body,
  request_encoding, sent_at, status, headers, body_excerpt, body_json?, body_text?}]}`.
  `headers` only holds the headers probe.py kept *at recording time* (its list grew during the day),
  `body_excerpt` is the first 160 characters of the body, `body_json` the full parsed JSON (only
  in recordings made after it was added), `body_text` the full text of small files (`keep_text`).
- bridge-log format (`/__bridge__/log` export): `[{id, started_at, persona, method, path, query,
  request_body, status, response_headers, response_body}]`. JSON bodies are parsed, strings longer
  than 2000 characters are cut and end with "…", text bodies are excerpts, binary bodies are
  `{"bytes": n}`.

Both were redacted: e-mails became `<email>` and `.env` values `<ENV_NAME>` (the requester's login
is an e-mail address, so `<HF_REQUESTER_LOGIN>` stands for an e-mail too).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .config import IDENTITY_ALIASES, OBSERVATIONS, RECORDED_ORIGINS

EXCERPT_LEN = 160  # probe.py: text[:160]
BRIDGE_MAX_STRING = 2000  # bridge exchange_log.MAX_STRING
TRUNCATION_MARK = "…"
PLACEHOLDER = re.compile(r"<[A-Za-z_]+>")  # redaction placeholders: <email>, <HF_REQUESTER_LOGIN>

# Headers whose ABSENCE in a recording is evidence that HF did not send them: the ones probe.py kept
# from its first version (git 7e14ba3: x-error-code, x-error-message, content-type, location, link,
# www-authenticate), all forwarded by the bridge too. Others (content-disposition, etag, x-repo-commit,
# x-linked-*) were added to probe.py during the day (07aa65a, 42cc2c8), so they only count for a
# recording where they appear at least once.
CORE_HEADERS = ("x-error-code", "x-error-message", "content-type", "location", "link", "www-authenticate")


@dataclass
class Expected:
    status: int
    headers: dict[str, str]  # lower-case names
    captured: frozenset[str]  # header names whose presence AND absence the recording proves
    # body: exactly one of these describes it
    body_kind: str  # "json" | "json-prefix" | "text" | "text-prefix" | "empty" | "unrecorded"
    body: Any = None  # parsed JSON, full text, or a prefix string
    strings_truncated: bool = False  # bridge log: JSON strings may end with "…" (cut at 2000)


@dataclass
class Step:
    id: str
    persona: str
    method: str
    path: str  # path + "?query", origin stripped
    body: Any
    encoding: str | None  # "json" | "form" | None
    expected: Expected
    sent_at: str | None = None
    note: str | None = None
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class Recording:
    name: str  # file stem without the date, e.g. "owner-walkthrough"
    path: Path
    format: str  # "probe" | "bridge-log"
    steps: list[Step]
    meta: dict


def strip_origin(url: str) -> str:
    for origin in RECORDED_ORIGINS:
        if url.startswith(origin):
            return url[len(origin) :] or "/"
    parts = urlsplit(url)
    if parts.scheme:
        raise ValueError(f"unexpected origin in recorded URL {url!r}")
    return url


def _is_json_type(content_type: str | None) -> bool:
    media = (content_type or "").split(";")[0].strip().lower()
    return media == "application/json" or media.endswith("+json")


def _probe_body(record: dict) -> tuple[str, Any]:
    if record["method"] == "HEAD":
        return "empty", ""
    if "body_json" in record:
        return "json", record["body_json"]
    if "body_text" in record:
        return "text", record["body_text"]
    excerpt = record.get("body_excerpt")
    if excerpt is None:  # probe.py drops HTML pages (<!doctype …)
        return "unrecorded", None
    if excerpt == "":
        return "empty", ""
    if _is_json_type(record["headers"].get("content-type")):
        try:
            return "json", json.loads(excerpt)  # a cut JSON document does not parse
        except ValueError:
            return "json-prefix", excerpt
    # Redaction ran after the cut and can shorten it, so an excerpt holding a placeholder may be cut.
    if len(excerpt) < EXCERPT_LEN and not PLACEHOLDER.search(excerpt):
        return "text", excerpt
    return "text-prefix", excerpt


def _load_probe(path: Path) -> Recording:
    data = json.loads(path.read_text())
    records = data["records"]
    captured = set(CORE_HEADERS)
    for record in records:
        captured |= {name.lower() for name in record["headers"]}
    steps = []
    for record in records:
        kind, body = _probe_body(record)
        steps.append(
            Step(
                id=record["id"],
                persona=IDENTITY_ALIASES[record["as"]],
                method=record["method"],
                path=strip_origin(record["url"]),
                body=record.get("request_body"),
                encoding=record.get("request_encoding"),
                expected=Expected(
                    status=record["status"],
                    headers={k.lower(): v for k, v in record["headers"].items()},
                    captured=frozenset(captured),
                    body_kind=kind,
                    body=body,
                ),
                sent_at=record.get("sent_at"),
                note=record.get("note"),
                raw=record,
            )
        )
    return Recording(_name(path), path, "probe", steps, data.get("_meta", {}))


def _bridge_body(entry: dict) -> tuple[str, Any]:
    body = entry.get("response_body")
    content_type = {k.lower(): v for k, v in entry["response_headers"].items()}.get("content-type")
    if entry["method"] == "HEAD" or body is None:
        return "empty", ""
    if isinstance(body, dict) and set(body) == {"bytes"} and not _is_json_type(content_type):
        return "unrecorded", None  # binary body, only its size was logged
    if _is_json_type(content_type):
        if isinstance(body, dict) and set(body) == {"bytes"}:
            return "unrecorded", None  # JSON over 256 kB, only its size was logged
        return "json", body
    if isinstance(body, str):
        if body.endswith(TRUNCATION_MARK) and len(body) == BRIDGE_MAX_STRING + 1:
            return "text-prefix", body[:-1]
        return "text", body
    return "unrecorded", None


def _load_bridge_log(path: Path) -> Recording:
    entries = json.loads(path.read_text())
    captured = set(CORE_HEADERS)
    for entry in entries:
        captured |= {name.lower() for name in entry["response_headers"]}
    steps = []
    for entry in entries:
        kind, body = _bridge_body(entry)
        query = entry.get("query") or ""
        steps.append(
            Step(
                id=str(entry["id"]),
                persona=IDENTITY_ALIASES[entry["persona"]],
                method=entry["method"],
                path=entry["path"] + (f"?{query}" if query else ""),
                body=entry.get("request_body"),
                encoding="json" if entry.get("request_body") is not None else None,
                expected=Expected(
                    status=entry["status"],
                    headers={k.lower(): v for k, v in entry["response_headers"].items()},
                    captured=frozenset(captured),
                    body_kind=kind,
                    body=body,
                    strings_truncated=True,
                ),
                sent_at=entry.get("started_at"),
                raw=entry,
            )
        )
    return Recording(_name(path), path, "bridge-log", steps, {})


def _name(path: Path) -> str:
    stem = path.stem
    # 2026-10-05-owner-walkthrough -> owner-walkthrough
    parts = stem.split("-", 3)
    return parts[3] if len(parts) == 4 and parts[0].isdigit() else stem


def load_recording(file_name: str) -> Recording:
    path = Path(file_name)
    if not path.is_absolute():
        path = OBSERVATIONS / file_name
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "records" in data:
        return _load_probe(path)
    if isinstance(data, list):
        return _load_bridge_log(path)
    raise ValueError(f"{path}: unknown recording format")
