"""Shared fixtures: a fresh store per test and a TestClient that never follows redirects.

The public URL is the bridge's (`http://127.0.0.1:8100`), so absolute URLs the clone builds can be
compared byte for byte with the walkthroughs recorded through the bridge.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from clone.app import create_app
from clone.store import Store, builtin_seed
from fastapi.testclient import TestClient

OBS = Path(__file__).resolve().parents[2] / "docs" / "hf-gated" / "observations"
PUBLIC_URL = "http://127.0.0.1:8100"
REPO = "Orosius/deltanet-mla-latent"
TOKENS = {"owner": "persona-owner", "requester": "persona-requester", "carol": "persona-carol"}


def auth(persona: str | None) -> dict[str, str]:
    """Headers for a persona (None or "anonymous" = no Authorization header)."""
    if persona in (None, "anonymous"):
        return {}
    return {"Authorization": f"Bearer {TOKENS.get(persona, persona)}"}


def load_observation(name: str):
    return json.loads((OBS / name).read_text())


def sandbox_with(requests: list[dict], **changes) -> dict:
    """The default seed with its requests replaced (and top-level fields overridden)."""
    seed = builtin_seed("sandbox")
    seed["requests"] = requests
    return seed | changes


def request_entry(status: str, timestamp: str, **extra) -> dict:
    return {"repo": REPO, "user": "TestingBOrig", "status": status, "timestamp": timestamp,
            "reviewedAt": None, "grantedBy": None, "fields": None, "emailShared": True} | extra


@pytest.fixture
def store() -> Store:
    return Store()


@pytest.fixture
def client(store: Store) -> TestClient:
    return TestClient(create_app(store, public_url=PUBLIC_URL), follow_redirects=False)
