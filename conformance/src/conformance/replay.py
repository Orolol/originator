"""Replay a recording against the backend under test and diff every step.

    seed (PUT /__clone__/state) -> replay each recorded request in order -> compare -> classify

Outcomes per step: `pass`, `fail` (a mismatch not covered by divergences.yaml), `diverged` (every
mismatch is a listed divergence), `skipped` (outside the backend surface, with the reason), or
`error` (transport failure).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from typing import Any
from urllib.parse import urlencode

import httpx
import yaml

from .compare import Actual, Context, Diff, TimestampTracker, compare_response
from .config import RECORDED_ORIGINS, SCENARIOS_FILE, auth_headers, backend_url
from .divergences import Divergence, load_divergences
from .recordings import Recording, Step, load_recording
from .seeds import pinned_timestamps, scenario_seed

USER_AGENT = "originator-conformance/1"


@dataclass
class StepResult:
    step: Step
    outcome: str
    diffs: list[Diff] = field(default_factory=list)
    reason: str = ""
    actual_status: int | None = None
    restricted_to: list[str] | None = None

    def as_dict(self) -> dict:
        s = self.step
        return {
            "id": s.id,
            "persona": s.persona,
            "method": s.method,
            "path": s.path,
            "request_body": s.body,
            "expected_status": s.expected.status,
            "actual_status": self.actual_status,
            "outcome": self.outcome,
            "reason": self.reason,
            "restricted_to": self.restricted_to,
            "diffs": [d.as_dict() for d in self.diffs],
        }


@dataclass
class ScenarioResult:
    name: str
    recording: str
    covers: list[str]
    stand_ins: bool
    mode: str  # "seeded" | "live"
    steps: list[StepResult] = field(default_factory=list)
    error: str | None = None
    seed: dict | None = None

    def counts(self) -> dict[str, int]:
        counts = {k: 0 for k in ("pass", "fail", "diverged", "skipped", "error")}
        for result in self.steps:
            counts[result.outcome] += 1
        return counts

    @property
    def ok(self) -> bool:
        return self.error is None and not any(r.outcome in ("fail", "error") for r in self.steps)

    def unexpected(self) -> list[tuple[StepResult, Diff]]:
        return [(r, d) for r in self.steps for d in r.diffs if d.divergence is None]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "recording": self.recording,
            "mode": self.mode,
            "covers": self.covers,
            "stand_ins": self.stand_ins,
            "error": self.error,
            "ok": self.ok,
            "counts": self.counts(),
            "steps": [r.as_dict() for r in self.steps],
        }


def load_manifest() -> dict:
    return yaml.safe_load(SCENARIOS_FILE.read_text())


def make_client(base_url: str | None = None) -> httpx.Client:
    return httpx.Client(base_url=base_url or backend_url(), follow_redirects=False, timeout=30.0,
                        headers={"User-Agent": USER_AGENT})


def send(client: httpx.Client, persona: str, method: str, path: str, body: Any = None,
         encoding: str | None = None, extra_headers: dict | None = None) -> httpx.Response:
    headers = {**auth_headers(persona), **(extra_headers or {})}
    content = None
    if body is not None:
        if encoding == "form":
            content = urlencode(body).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            content = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
    url = str(client.base_url).rstrip("/") + path
    return client.request(method, url, content=content, headers=headers)


def to_actual(response: httpx.Response) -> Actual:
    headers: dict[str, str] = {}
    for name, value in response.headers.multi_items():
        name = name.lower()
        headers[name] = f"{headers[name]}, {value}" if name in headers else value
    return Actual(response.status_code, headers, response.content)


def apply_divergences(scenario: str, step_id: str, diffs: list[Diff], divergences: list[Divergence]) -> None:
    for diff in diffs:
        for entry in divergences:
            if entry.covers(scenario, step_id, diff.field):
                diff.divergence = entry.id
                break


def classify(diffs: list[Diff]) -> str:
    if not diffs:
        return "pass"
    return "diverged" if all(d.divergence for d in diffs) else "fail"


def put_state(client: httpx.Client, document: dict) -> None:
    response = client.put("/__clone__/state", json=document)
    if response.status_code >= 300:
        raise RuntimeError(f"PUT /__clone__/state -> {response.status_code}: {response.text[:500]}")


def run_scenario(name: str, client: httpx.Client | None = None, divergences: list[Divergence] | None = None,
                 live: bool = False) -> ScenarioResult:
    manifest = load_manifest()
    spec = manifest["scenarios"][name]
    recording: Recording = load_recording(spec["recording"])
    divergences = load_divergences() if divergences is None else divergences
    own_client = client is None
    client = client or make_client()
    scenario_key = f"live:{name}" if live else name
    result = ScenarioResult(scenario_key, spec["recording"], spec.get("covers", []), bool(spec.get("stand_ins")),
                            "live" if live else "seeded")
    try:
        pinned: set[str] = set()
        if live:
            selected = set(manifest.get("live", {}).get(name, []))
        else:
            document = scenario_seed(name)
            result.seed = document
            put_state(client, document)
            pinned = pinned_timestamps(document)
        ctx = Context(TimestampTracker(pinned), str(client.base_url).rstrip("/"), RECORDED_ORIGINS)
        skip = spec.get("skip") or {}
        restrict = spec.get("compare_only") or {}
        for step in recording.steps:
            if live and step.id not in selected:
                result.steps.append(StepResult(step, "skipped", reason="not in the live read-only selection"))
                continue
            if live and step.method not in ("GET", "HEAD"):
                raise AssertionError(f"live mode refuses {step.method} {step.path}")  # never write upstream
            if step.id in skip:
                result.steps.append(StepResult(step, "skipped", reason=skip[step.id]))
                continue
            try:
                response = send(client, step.persona, step.method, step.path, step.body, step.encoding)
            except httpx.HTTPError as error:
                result.steps.append(StepResult(step, "error", reason=f"{type(error).__name__}: {error}"))
                continue
            diffs = compare_response(step.expected, to_actual(response), ctx)
            restricted = None
            if step.id in restrict:
                restricted = restrict[step.id]["fields"]
                diffs = [d for d in diffs if any(fnmatchcase(d.field, g) for g in restricted)]
            apply_divergences(scenario_key, step.id, diffs, divergences)
            result.steps.append(StepResult(step, classify(diffs), diffs, restrict.get(step.id, {}).get("reason", ""),
                                           response.status_code, restricted))
    except Exception as error:  # seeding or harness failure: report it, do not hide it
        result.error = f"{type(error).__name__}: {error}"
    finally:
        if own_client:
            client.close()
    return result


def results_from_json(payload: dict, divergences: list[Divergence]) -> list[ScenarioResult]:
    """Rebuild a saved run (report JSON) and re-judge it against the current divergences, without sending
    any request: used to re-render a live run after divergences.yaml changed."""
    manifest = load_manifest()
    results = []
    for saved in payload["scenarios"]:
        base = saved["name"].removeprefix("live:")
        steps = {s.id: s for s in load_recording(manifest["scenarios"][base]["recording"]).steps}
        result = ScenarioResult(saved["name"], saved["recording"], saved["covers"], saved["stand_ins"], saved["mode"],
                                error=saved["error"])
        for item in saved["steps"]:
            diffs = [Diff(d["field"], d["expected"], d["actual"], d["detail"]) for d in item["diffs"]]
            outcome = item["outcome"]
            if outcome in ("pass", "fail", "diverged"):
                apply_divergences(saved["name"], item["id"], diffs, divergences)
                outcome = classify(diffs)
            result.steps.append(StepResult(steps[item["id"]], outcome, diffs, item["reason"], item["actual_status"],
                                           item["restricted_to"]))
        results.append(result)
    return results


def stale_divergences(results: list[ScenarioResult], divergences: list[Divergence]) -> list[Divergence]:
    """Replay divergences that a run could have used but did not: they overstate the known gaps.

    An entry is judged only when every scenario its pattern matches in `results` ran without a harness
    error (a seeding failure proves nothing). Rule-test entries (`rules:*`) are strict xfails instead.
    """
    stale = []
    for entry in divergences:
        if entry.scenario.startswith("rules:"):
            continue
        matching = [r for r in results if fnmatchcase(r.name, entry.scenario)]
        if not matching or any(r.error for r in matching):
            continue
        used = any(d.divergence == entry.id for r in matching for step in r.steps for d in step.diffs)
        if not used:
            stale.append(entry)
    return stale


def stale_message(entry: Divergence) -> str:
    return f"stale divergence {entry.id}: remove or re-justify (it covers no mismatch in {entry.scenario})"


def run_scenarios(names: list[str], client: httpx.Client | None = None, live: bool = False) -> list[ScenarioResult]:
    divergences = load_divergences()
    own = client is None
    client = client or make_client()
    try:
        return [run_scenario(name, client, divergences, live=live) for name in names]
    finally:
        if own:
            client.close()


def scenario_names() -> list[str]:
    return list(load_manifest()["scenarios"])


def live_scenario_names() -> list[str]:
    return list((load_manifest().get("live") or {}))
