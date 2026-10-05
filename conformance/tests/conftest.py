"""Shared fixtures.

`huggingface_hub` reads HF_ENDPOINT once, at import time, and its access-request methods use that
module constant instead of `HfApi(endpoint=...)` (docs/hf-gated/client-library.md, api.md §4). So the
environment is pinned here, before any test module can import it. HF_HOME points to a throwaway
directory so a token cached on this machine can never be sent to the backend.
"""

from __future__ import annotations

import os
import sys
import tempfile

from conformance.config import backend_url

assert "huggingface_hub" not in sys.modules, "huggingface_hub imported before conftest pinned HF_ENDPOINT"
os.environ["HF_ENDPOINT"] = backend_url()
os.environ["HF_HOME"] = tempfile.mkdtemp(prefix="conformance-hf-home-")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HF_HUB_OFFLINE"):
    os.environ.pop(name, None)

import httpx  # noqa: E402
import pytest  # noqa: E402

from conformance.clone_api import Backend  # noqa: E402
from conformance.divergences import load_divergences  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """Known divergences of rule tests live in divergences.yaml too (scenario `rules:<module>`, step = test
    name, parameters included or not). They become strict xfails: the assertion is unchanged, the failure is
    expected and labelled, and an unexpected pass turns the run red so the entry gets removed."""
    entries = [d for d in load_divergences() if d.scenario.startswith("rules:")]
    for item in items:
        module = item.module.__name__.rsplit(".", 1)[-1]
        name = getattr(item, "originalname", item.name)
        for entry in entries:
            if entry.covers(f"rules:{module}", item.name, "*") or entry.covers(f"rules:{module}", name, "*"):
                item.add_marker(pytest.mark.xfail(strict=True, reason=f"{entry.id} ({entry.rule}): {entry.reason}"))


def _reachable(url: str) -> str | None:
    try:
        httpx.get(f"{url}/__clone__/health", timeout=3.0)
        return None
    except httpx.HTTPError as error:
        return f"{type(error).__name__}: {error}"


@pytest.fixture(scope="session")
def backend_base() -> str:
    url = backend_url()
    problem = _reachable(url)
    if problem:
        pytest.fail(f"backend not reachable at {url} ({problem}). Start the clone "
                    f"(`uv run --project clone clone`, port 8200) or set BACKEND_URL.", pytrace=False)
    return url


@pytest.fixture(scope="session")
def is_clone(backend_base: str) -> bool:
    response = httpx.get(f"{backend_base}/__clone__/health", timeout=3.0)
    return response.status_code == 200


@pytest.fixture
def be(backend_base: str, is_clone: bool, request: pytest.FixtureRequest):
    if not is_clone and request.node.get_closest_marker("live") is None:
        pytest.fail(f"{backend_base} has no /__clone__/ control endpoints: seeded tests need the clone "
                    "(live tests are opt-in with -m live)", pytrace=False)
    backend = Backend(backend_base)
    yield backend
    backend.close()
