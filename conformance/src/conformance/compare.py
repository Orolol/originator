"""Compare one backend response with one recorded response.

Only legitimately volatile things are normalised (docs/method.md §3); every normalisation is listed
in NORMALISATIONS and printed in the report. Everything else must match exactly: status,
`X-Error-Code`, `X-Error-Message`, `Content-Type` (media type and charset), `Content-Disposition`,
`WWW-Authenticate`, `X-Repo-Commit`, file `ETag`s, the `Location` path and query, JSON structure,
keys, key order and values, and text bodies.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .recordings import TRUNCATION_MARK, Expected

NORMALISATIONS = [
    ("e-mail addresses", "Recordings are redacted (`<email>`, or `<HF_REQUESTER_LOGIN>` whose value is an "
     "e-mail). Every e-mail address in the backend's response becomes `<email>` before comparing; "
     "presence and position are still checked."),
    ("timestamps", "Times the backend generates come from its virtual clock, not the Hub's wall clock. "
     "Each recorded ISO timestamp is matched to the backend's: timestamps present in the initial seed "
     "must come back verbatim; the others must keep the recorded equalities (same recorded value -> "
     "same backend value, different -> different) and the recorded order, and use HF's format "
     "`YYYY-MM-DDTHH:MM:SS.mmmZ`."),
    ("ETag of generated responses", "JSON, HTML and error bodies carry a weak ETag that hashes the "
     "serialised body; it is ignored. File ETags (responses with Content-Disposition or "
     "X-Repo-Commit) are compared, after stripping a `W/` prefix: HF weakens the ETag when it "
     "gzips the response, which the bridge's HTTP client asks for and probe.py does not."),
    ("Content-Length", "Ignored (the bridge drops it; body bytes are compared instead)."),
    ("URL origins", "In `Location`, in `Link` targets and in the `Redirecting to <url>` text of a 3xx "
     "body, the origins https://huggingface.co, the bridge (http://127.0.0.1:8100) and the backend "
     "under test become `<origin>`. Absolute vs relative is kept. Origins inside messages (for "
     "example `Visit https://huggingface.co/{id} to ask for access.`) are NOT normalised."),
    ("cut recordings", "Where a recording only kept a prefix (probe excerpts of 160 characters, bridge-log "
     "strings cut at 2000 characters and marked `…`), the backend's value must start with it. A cut "
     "JSON excerpt is compared against the backend's JSON re-serialised compactly "
     "(`separators=(',', ':')`, as HF serialises), so whitespace is not compared but key order is."),
    ("headers not captured", "A header is checked for presence/absence only if the recording could have "
     "captured it: those probe.py kept from its first version (X-Error-Code, X-Error-Message, Content-Type, "
     "Location, Link, WWW-Authenticate; git 7e14ba3) always; the others (Content-Disposition, ETag, "
     "X-Repo-Commit, X-Linked-*) only in recordings where they appear at least once, because probe.py's list "
     "grew during the day (07aa65a, 42cc2c8) and the bridge forwards a fixed subset."),
]

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LOGIN_PLACEHOLDER = re.compile(r"<HF_[A-Z_]*LOGIN>")
ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
HF_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
TS_ANYWHERE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
PARTIAL_TS_AT_END = re.compile(r'"\d{4}-[0-9T:.\-]*$')
PARTIAL_PLACEHOLDER_AT_END = re.compile(r"<[A-Za-z_]*$")
REDIRECT_TEXT = re.compile(r"(Redirecting to )(https?://[^/\s]+)")
MAX_DIFFS_PER_STEP = 40


@dataclass
class Diff:
    field: str
    expected: Any
    actual: Any
    detail: str = ""
    divergence: str | None = None  # id of the accepted divergence entry that covers it

    def as_dict(self) -> dict:
        return {
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
            "divergence": self.divergence,
        }


@dataclass
class Actual:
    status: int
    headers: dict[str, str]  # lower-case names
    body: bytes


def norm_email(value: str) -> str:
    return EMAIL.sub("<email>", value)


def norm_expected_str(value: str) -> str:
    return LOGIN_PLACEHOLDER.sub("<email>", value)


def norm_json_emails(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: norm_json_emails(v) for k, v in node.items()}
    if isinstance(node, list):
        return [norm_json_emails(v) for v in node]
    if isinstance(node, str):
        return norm_email(node)
    return node


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TimestampTracker:
    """Matches recorded timestamps to backend timestamps across a whole scenario."""

    def __init__(self, pinned: set[str]):
        self.pinned = set(pinned)
        self.exp_to_act: dict[str, str] = {ts: ts for ts in self.pinned}
        self.act_to_exp: dict[str, str] = {ts: ts for ts in self.pinned}

    def check(self, where: str, expected: str, actual: Any) -> list[Diff]:
        if not isinstance(actual, str) or not ISO_TS.match(actual):
            return [Diff(where, expected, actual, "expected an ISO-8601 UTC timestamp")]
        diffs = []
        if HF_TS.match(expected) and not HF_TS.match(actual):
            diffs.append(Diff(where, expected, actual, "timestamp format differs from HF's YYYY-MM-DDTHH:MM:SS.mmmZ"))
        if expected in self.pinned:
            if actual != expected:
                diffs.append(Diff(where, expected, actual, "seeded timestamp must come back verbatim"))
            return diffs
        known = self.exp_to_act.get(expected)
        if known is not None:
            if known != actual:
                diffs.append(Diff(where, expected, actual,
                                  f"recorded value seen before maps to backend value {known}; equality not kept"))
            return diffs
        other = self.act_to_exp.get(actual)
        if other is not None:
            diffs.append(Diff(where, expected, actual,
                              f"backend value already stands for a different recorded time ({other})"))
            return diffs
        e_new, a_new = _parse_ts(expected), _parse_ts(actual)
        for e_old, a_old in self.exp_to_act.items():
            e_cmp = (e_new > _parse_ts(e_old)) - (e_new < _parse_ts(e_old))
            a_cmp = (a_new > _parse_ts(a_old)) - (a_new < _parse_ts(a_old))
            if e_cmp != a_cmp:
                diffs.append(Diff(where, expected, actual,
                                  f"order differs from recording relative to {e_old} (backend {a_old})"))
                break
        self.exp_to_act[expected] = actual
        self.act_to_exp[actual] = expected
        return diffs


@dataclass
class Context:
    timestamps: TimestampTracker
    backend_origin: str
    recorded_origins: tuple[str, ...]
    strings_truncated: bool = False
    diffs: list[Diff] = field(default_factory=list)

    def origins(self) -> tuple[str, ...]:
        return (*self.recorded_origins, self.backend_origin)


def compare_json(expected: Any, actual: Any, where: str, ctx: Context) -> list[Diff]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [Diff(where, "object", _type_name(actual), "type differs")]
        diffs = []
        exp_keys, act_keys = list(expected), list(actual)
        if exp_keys != act_keys:
            missing = [k for k in exp_keys if k not in actual]
            extra = [k for k in act_keys if k not in expected]
            if missing or extra:
                diffs.append(Diff(f"{where}:keys", exp_keys, act_keys, f"missing {missing}; unexpected {extra}"))
            else:
                diffs.append(Diff(f"{where}:key-order", exp_keys, act_keys, "same keys, different order"))
        for key in exp_keys:
            if key in actual:
                diffs += compare_json(expected[key], actual[key], f"{where}.{key}", ctx)
        return diffs
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [Diff(where, "array", _type_name(actual), "type differs")]
        diffs = []
        if len(expected) != len(actual):
            diffs.append(Diff(f"{where}:length", len(expected), len(actual), "array length differs"))
        for index, (exp_item, act_item) in enumerate(zip(expected, actual)):
            diffs += compare_json(exp_item, act_item, f"{where}[{index}]", ctx)
        return diffs
    if isinstance(expected, str):
        exp = norm_expected_str(expected)
        if not isinstance(actual, str):
            return [Diff(where, expected, actual, "type differs")]
        act = norm_email(actual)
        if ctx.strings_truncated and exp.endswith(TRUNCATION_MARK) and len(exp) == 2001:
            return [] if act.startswith(exp[:-1]) else [Diff(where, exp, act, "recorded prefix (cut at 2000) not matched")]
        if ISO_TS.match(exp):
            return ctx.timestamps.check(where, exp, act)
        return [] if exp == act else [Diff(where, exp, act)]
    # numbers, booleans, null: same value and same JSON type (True is not 1)
    if type(expected) is not type(actual) or expected != actual:
        if isinstance(expected, float) and isinstance(actual, (int, float)) and not isinstance(actual, bool):
            if float(actual) == expected:
                return []
        return [Diff(where, expected, actual)]
    return []


def _type_name(value: Any) -> str:
    return {dict: "object", list: "array", str: "string", bool: "boolean", type(None): "null"}.get(
        type(value), "number"
    )


def _norm_content_type(value: str | None) -> str | None:
    if value is None:
        return None
    parts = [p.strip().lower().replace('"', "") for p in value.split(";") if p.strip()]
    return "; ".join([parts[0], *sorted(parts[1:])]) if parts else ""


def _norm_origin_url(value: str, ctx: Context) -> str:
    for origin in sorted(ctx.origins(), key=len, reverse=True):
        if value.startswith(origin) and (len(value) == len(origin) or value[len(origin)] in "/?#"):
            return "<origin>" + value[len(origin):]
    return value


def _norm_link(value: str, ctx: Context) -> str:
    return re.sub(r"<([^>]*)>", lambda m: "<" + _norm_origin_url(m.group(1), ctx) + ">", value)


def _is_file_response(expected: Expected) -> bool:
    return 200 <= expected.status < 400 and (
        "x-repo-commit" in expected.headers or "content-disposition" in expected.headers
    )


def compare_headers(expected: Expected, actual: Actual, ctx: Context) -> list[Diff]:
    diffs = []
    for name in sorted(expected.captured):
        if name == "content-length":
            continue
        exp, act = expected.headers.get(name), actual.headers.get(name)
        if name == "etag":
            if not _is_file_response(expected):
                continue
            exp = exp.removeprefix("W/") if exp else exp
            act = act.removeprefix("W/") if act else act
        elif name == "content-type":
            exp, act = _norm_content_type(exp), _norm_content_type(act)
        elif name == "location":
            exp = _norm_origin_url(exp, ctx) if exp else exp
            act = _norm_origin_url(act, ctx) if act else act
        elif name == "link":
            exp = _norm_link(exp, ctx) if exp else exp
            act = _norm_link(act, ctx) if act else act
        if exp is not None:
            exp = norm_expected_str(exp)
        if act is not None:
            act = norm_email(act)
        if exp != act:
            detail = "missing" if act is None else ("unexpected" if exp is None else "")
            diffs.append(Diff(f"header:{name}", exp, act, detail))
    return diffs


def _norm_redirect_text(text: str, ctx: Context) -> str:
    return REDIRECT_TEXT.sub(lambda m: m.group(1) + _norm_origin_url(m.group(2), ctx), text)


def compare_body(expected: Expected, actual: Actual, ctx: Context) -> list[Diff]:
    kind = expected.body_kind
    if kind == "unrecorded":
        return []
    if kind == "empty":
        return [] if actual.body == b"" else [Diff("body", "", _preview(actual.body), "expected an empty body")]
    text = actual.body.decode("utf-8", errors="replace")
    if kind in ("json", "json-prefix"):
        try:
            parsed = json.loads(text)
        except ValueError:
            return [Diff("body", "JSON", _preview(actual.body), "body is not JSON")]
        if kind == "json":
            ctx.strings_truncated = expected.strings_truncated
            return compare_json(expected.body, parsed, "body$", ctx)
        compact = json.dumps(norm_json_emails(parsed), ensure_ascii=False, separators=(",", ":"))
        prefix = norm_expected_str(expected.body)
        prefix = PARTIAL_PLACEHOLDER_AT_END.sub("", PARTIAL_TS_AT_END.sub("", prefix))
        if TS_ANYWHERE.sub("<ts>", compact).startswith(TS_ANYWHERE.sub("<ts>", prefix)):
            return []
        return [Diff("body", prefix, compact[: len(prefix) + 40], "recorded JSON excerpt is not a prefix of the "
                     "backend's compact JSON (timestamps masked)")]
    exp_text = norm_expected_str(expected.body)
    act_text = norm_email(text)
    if 300 <= expected.status < 400:
        exp_text, act_text = _norm_redirect_text(exp_text, ctx), _norm_redirect_text(act_text, ctx)
    if kind == "text":
        return [] if exp_text == act_text else [Diff("body", exp_text, _cut(act_text))]
    if kind == "text-prefix":
        return [] if act_text.startswith(exp_text) else [Diff("body", exp_text, _cut(act_text), "recorded prefix not matched")]
    raise ValueError(kind)


def _preview(body: bytes) -> str:
    return _cut(body.decode("utf-8", errors="replace"))


def _cut(text: str, limit: int = 400) -> str:
    return text if len(text) <= limit else text[:limit] + f"…[+{len(text) - limit}]"


def compare_response(expected: Expected, actual: Actual, ctx: Context) -> list[Diff]:
    diffs = []
    if expected.status != actual.status:
        diffs.append(Diff("status", expected.status, actual.status))
    diffs += compare_headers(expected, actual, ctx)
    diffs += compare_body(expected, actual, ctx)
    return diffs
