"""Zod-style request validation, formatted the way HF's server reports it.

api.md §3 "Validation message format" [OBS 2026-10-05, W s7]: the JSON body is zod's pretty format
(`✖ <message>` plus `  → at <path>` when the issue has a path, issues sorted by path depth), and
`X-Error-Message` is an ASCII-sanitised copy. Observed messages: invalid enum, string too big,
number too small, and the user/userId refinement. The other messages below follow the same
wording family for checks nobody has recorded yet: Provisional (Q-9).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

MISSING: Any = object()  # a key absent from the input (zod's `undefined`)


@dataclass(frozen=True)
class Issue:
    message: str
    path: tuple[str | int, ...] = ()


class ValidationFailed(Exception):
    def __init__(self, issues: Sequence[Issue]):
        super().__init__(issues)
        self.issues = list(issues)

    def pretty(self) -> str:
        return prettify(self.issues)


def _dot_path(path: Iterable[str | int]) -> str:
    out = ""
    for seg in path:
        if isinstance(seg, int):
            out += f"[{seg}]"
        elif re.search(r"[^\w$]", seg):
            out += f"[{json.dumps(seg)}]"
        else:
            out += ("." if out else "") + seg
    return out


def prettify(issues: Sequence[Issue]) -> str:
    lines: list[str] = []
    for issue in sorted(issues, key=lambda i: len(i.path)):
        lines.append(f"✖ {issue.message}")
        if issue.path:
            lines.append(f"  → at {_dot_path(issue.path)}")
    return "\n".join(lines)


def header_safe(text: str) -> str:
    """X-Error-Message form: non-ASCII → `*`, whitespace runs → one space [OBS]."""
    return re.sub(r"\s+", " ", "".join(c if ord(c) < 128 else "*" for c in text))


def type_name(value: Any) -> str:
    if value is MISSING:
        return "undefined"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "NaN" if value != value else "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def _expected(kind: str, value: Any) -> str:
    return f"Invalid input: expected {kind}, received {type_name(value)}"


class Checker:
    """Collects issues for one input object, field by field, in schema order (zod's order)."""

    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def add(self, message: str, *path: str | int) -> None:
        self.issues.append(Issue(message, tuple(path)))

    def raise_if_any(self) -> None:
        if self.issues:
            raise ValidationFailed(self.issues)

    def obj(self, value: Any, *path: str | int, kind: str = "object") -> bool:
        if isinstance(value, dict):
            return True
        self.add(_expected(kind, value), *path)
        return False

    def string(self, value: Any, *path: str | int, optional: bool = True, min_len: int | None = None,
               max_len: int | None = None, pattern: str | None = None) -> None:
        if value is MISSING and optional:
            return
        if not isinstance(value, str):
            self.add(_expected("string", value), *path)
            return
        if min_len is not None and len(value) < min_len:
            self.add(f"Too small: expected string to have >={min_len} characters", *path)
        if max_len is not None and len(value) > max_len:
            # [OBS W s7-reject-reason-too-long]
            self.add(f"Too big: expected string to have <={max_len} characters", *path)
        if pattern is not None and not re.search(pattern, value):
            self.add(f"Invalid string: must match pattern /{pattern}/", *path)

    def enum(self, value: Any, options: Sequence[str], *path: str | int, optional: bool = False) -> None:
        if value is MISSING and optional:
            return
        if value not in options or not isinstance(value, str):
            # [OBS W s7-handle-bad-status]
            self.add("Invalid option: expected one of " + "|".join(json.dumps(o) for o in options), *path)

    def boolean(self, value: Any, *path: str | int) -> None:
        if value is not MISSING and not isinstance(value, bool):
            self.add(_expected("boolean", value), *path)

    def array(self, value: Any, *path: str | int, min_items: int, max_items: int) -> bool:
        if not isinstance(value, list):
            self.add(_expected("array", value), *path)
            return False
        if len(value) < min_items:
            self.add(f"Too small: expected array to have >={min_items} items", *path)
        if len(value) > max_items:
            self.add(f"Too big: expected array to have <={max_items} items", *path)
        return True

    def int_query(self, raw: str | None, name: str, *, minimum: int, maximum: int) -> int | None:
        """A coerced integer query parameter (`limit`)."""
        if raw is None:
            return None
        try:
            number = float(raw) if raw.strip() else 0.0  # Number("") is 0 in JS
        except ValueError:
            number = float("nan")
        if not math.isfinite(number):
            self.add(_expected("number", float("nan")), name)
            return None
        if number != int(number):
            self.add("Invalid input: expected int, received number", name)
            return None
        if number < minimum:
            self.add(f"Too small: expected number to be >={minimum}", name)  # [OBS W s7-list-limit-5]
        if number > maximum:
            self.add(f"Too big: expected number to be <={maximum}", name)
        return int(number)


USER_REFINE = "Either userId or user must be provided, but not both"  # [OBS W s7-handle-no-user]
USER_ID_PATTERN = "^[0-9a-fA-F]{24}$"


def check_user_ref(c: Checker, body: dict, *path: str | int) -> None:
    """`{user | userId}` fields (REV-5): schema checks only; the refinement runs afterwards."""
    c.string(body.get("userId", MISSING), *path, "userId", min_len=24, max_len=24, pattern=USER_ID_PATTERN)
    c.string(body.get("user", MISSING), *path, "user")


def refine_user_ref(c: Checker, body: dict, *path: str | int) -> None:
    """REV-5: exactly one of `user` / `userId`. Provisional (Q-9): like zod, the refinement only
    runs once the field checks passed, so it is reported alone."""
    if ("user" in body) == ("userId" in body):
        c.add(USER_REFINE, *path)
