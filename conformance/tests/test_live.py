"""Live mode (opt-in, `-m live`): read-only replays through the bridge to huggingface.co.

    BACKEND_URL=http://127.0.0.1:8100 uv run --project conformance pytest conformance/tests -m live

Only GET/HEAD steps listed under `live:` in scenarios.yaml are sent (the replay refuses anything
else), so nothing changes upstream. The bridge must already be running; this suite never starts it.
"""

from __future__ import annotations

import pytest

from conformance.config import BRIDGE_URL, backend_url
from conformance.replay import live_scenario_names, run_scenario

pytestmark = pytest.mark.live


@pytest.mark.parametrize("scenario", live_scenario_names())
def test_live_replay(scenario: str, be):
    if backend_url() != BRIDGE_URL:
        pytest.skip(f"live mode replays against the bridge ({BRIDGE_URL}); BACKEND_URL={backend_url()}")
    result = run_scenario(scenario, be.client, live=True)
    assert result.error is None, result.error
    problems = [(r.step.id, d.field, d.expected, d.actual) for r, d in result.unexpected()]
    assert not problems, problems
