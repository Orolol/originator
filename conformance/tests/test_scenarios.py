"""Replay every real-Hub recording against the backend (one test per scenario), then check that every
listed replay divergence was actually needed.

Per-step detail: `uv run --project conformance conformance-report` (conformance/reports/latest.md).
A step fails on any mismatch that conformance/divergences.yaml does not list; the run fails on a
listed divergence that covers no mismatch (stale), so the known-gaps list cannot overstate the gaps.
"""

from __future__ import annotations

import pytest

from conformance.divergences import load_divergences
from conformance.replay import run_scenarios, scenario_names, stale_divergences, stale_message


def _format(result) -> str:
    lines = [f"{result.name}: {result.counts()}"]
    for step_result in result.steps:
        if step_result.outcome == "error":
            lines.append(f"  {step_result.step.id}: transport error {step_result.reason}")
        for diff in step_result.diffs:
            if diff.divergence is None:
                lines.append(f"  {step_result.step.id} {diff.field}: expected {diff.expected!r} got {diff.actual!r}"
                             f"{' (' + diff.detail + ')' if diff.detail else ''}")
    return "\n".join(lines[:80])


@pytest.fixture(scope="module")
def replays(backend_base, is_clone):
    if not is_clone:
        pytest.fail(f"{backend_base} has no /__clone__/ control endpoints: replays need the clone", pytrace=False)
    from conformance.replay import make_client

    with make_client(backend_base) as client:
        return {r.name: r for r in run_scenarios(scenario_names(), client)}


@pytest.mark.parametrize("scenario", scenario_names())
def test_replay(scenario: str, replays):
    result = replays[scenario]
    assert result.error is None, f"{scenario}: {result.error}"
    assert result.ok, _format(result)


def test_no_stale_divergences(replays):
    stale = stale_divergences(list(replays.values()), load_divergences())
    assert not stale, "\n".join(stale_message(entry) for entry in stale)
