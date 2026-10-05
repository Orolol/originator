"""Live mode (opt-in, `-m live`): read-only replays through the bridge to huggingface.co.

    BACKEND_URL=http://127.0.0.1:8100 uv run --project conformance pytest conformance/tests -m live

Only GET/HEAD steps listed under `live:` in scenarios.yaml are sent (the replay refuses anything
else), so nothing changes upstream. The bridge must already be running; this suite never starts it.
"""

from __future__ import annotations

import pytest

from conformance.config import BRIDGE_URL, backend_url
from conformance.divergences import load_divergences
from conformance.replay import live_scenario_names, make_client, run_scenarios, stale_divergences, stale_message

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def live_replays(backend_base):
    if backend_url() != BRIDGE_URL:
        pytest.skip(f"live mode replays against the bridge ({BRIDGE_URL}); BACKEND_URL={backend_url()}")
    with make_client(backend_base) as client:
        return {r.name: r for r in run_scenarios(live_scenario_names(), client, live=True)}


@pytest.mark.parametrize("scenario", live_scenario_names())
def test_live_replay(scenario: str, live_replays):
    result = live_replays[f"live:{scenario}"]
    assert result.error is None, result.error
    problems = [(r.step.id, d.field, d.expected, d.actual) for r, d in result.unexpected()]
    assert not problems, problems


def test_live_no_stale_divergences(live_replays):
    stale = stale_divergences(list(live_replays.values()), load_divergences())
    assert not stale, "\n".join(stale_message(entry) for entry in stale)
