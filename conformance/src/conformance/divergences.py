"""Accepted, documented mismatches (conformance/divergences.yaml).

An entry covers a diff when `scenario`, `step` and `field` all match (shell-style globs, so
`header:*` or `body$[*].user.email` work; `step` and `field` may also be lists of globs). Every entry
must name a rule or question ID and a reason traced to the KB; anything not covered fails the scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

from .config import DIVERGENCES_FILE

REQUIRED = ("id", "scenario", "step", "field", "rule", "reason")


@dataclass
class Divergence:
    id: str
    scenario: str
    step: str | list[str]
    field: str | list[str]
    rule: str
    reason: str
    evidence: str = ""

    def covers(self, scenario: str, step: str, field: str) -> bool:
        return fnmatchcase(scenario, self.scenario) and _any(step, self.step) and _any(field, self.field)


def _any(value: str, patterns: str | list[str]) -> bool:
    return any(fnmatchcase(value, p) for p in ([patterns] if isinstance(patterns, str) else patterns))


def load_divergences(path: Path = DIVERGENCES_FILE) -> list[Divergence]:
    data = yaml.safe_load(path.read_text()) or {}
    entries = data.get("divergences") or []
    result = []
    for entry in entries:
        missing = [key for key in REQUIRED if not entry.get(key)]
        if missing:
            raise ValueError(f"{path}: divergence {entry.get('id', '?')} lacks {missing}")
        result.append(Divergence(**{k: v if isinstance(v, list) else str(v) for k, v in entry.items()}))
    ids = [d.id for d in result]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate divergence ids")
    return result
