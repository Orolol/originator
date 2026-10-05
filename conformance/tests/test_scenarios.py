"""Replay every real-Hub recording against the backend (one test per scenario).

Per-step detail: `uv run --project conformance conformance-report` (conformance/reports/latest.md).
A step fails on any mismatch that conformance/divergences.yaml does not list.
"""

from __future__ import annotations

import pytest

from conformance.replay import run_scenario, scenario_names


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


@pytest.mark.parametrize("scenario", scenario_names())
def test_replay(scenario: str, be):
    result = run_scenario(scenario, be.client)
    assert result.error is None, f"{scenario}: {result.error}"
    assert result.ok, _format(result)
