"""Fast offline fixtures: the bridge runs in-process against a scripted `httpx.MockTransport`."""

from __future__ import annotations

import re
import warnings

import httpx
import pytest
from starlette.exceptions import StarletteDeprecationWarning

# Starlette's TestClient prefers `httpx2`; the app itself uses `httpx`, so keep the deprecated path quiet.
warnings.filterwarnings("ignore", message="Using `httpx` with", category=StarletteDeprecationWarning)

from fastapi.testclient import TestClient

from bridge.app import create_app
from bridge.config import Settings

REPO = "Orosius/deltanet-mla-latent"
OTHER_REPO = "someone/else"
PUBLIC_URL = "http://bridge.test"
# Fake values: the offline tests never read the real `.env`.
OWNER_TOKEN = "hf_FAKE_owner_0123456789"
REQUESTER_TOKEN = "hf_FAKE_requester_9876543210"


def pytest_configure(config):
    config.addinivalue_line("markers", "live: read-only smoke tests against the real huggingface.co")


def pytest_collection_modifyitems(config, items):
    """Live tests are opt-in even when pytest ignores pyproject's addopts (e.g. run from the repo root)."""
    if re.search(r"(?<!not )\blive\b", config.getoption("-m") or ""):
        return
    skip = pytest.mark.skip(reason="live test: opt in with `-m live`")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


class FakeUpstream:
    """Transport handler: records every request and answers with `responder(request)`."""

    def __init__(self, responder=None):
        self.requests: list[httpx.Request] = []
        self.responder = responder or (lambda request: httpx.Response(200, json={"ok": True}))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responder(request)


@pytest.fixture
def make_bridge(tmp_path):
    """Factory `make_bridge(responder=None, **settings)` -> (client, upstream)."""
    clients: list[TestClient] = []

    def make(responder=None, **overrides):
        upstream = FakeUpstream(responder)
        defaults = {
            "upstream": "https://huggingface.co",
            "public_url": PUBLIC_URL,
            "repos": (REPO,),
            "tokens": {"owner": OWNER_TOKEN, "requester": REQUESTER_TOKEN},
            "log_file": tmp_path / "bridge.jsonl",
        }
        settings = Settings(**{**defaults, **overrides})
        app = create_app(settings, transport=httpx.MockTransport(upstream))
        client = TestClient(app, follow_redirects=False)  # the bridge must never follow redirects
        client.__enter__()
        clients.append(client)
        return client, upstream

    yield make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def bridge(make_bridge):
    return make_bridge()
