"""Read-only smoke tests against the real huggingface.co, through the bridge app.

Skipped by default; run with `uv run --project bridge pytest -m live`. Needs the tokens in the
repo-root `.env`. GET/HEAD only: state-changing calls on the live Hub are never made from tests.
"""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from bridge.app import create_app
from bridge.config import Settings

pytestmark = pytest.mark.live

REPO = "OwnerOfTheGatedModel/tiny-gated-model"
OWNER = {"Authorization": "Bearer persona-owner"}
REQUESTER = {"Authorization": "Bearer persona-requester"}


class ReadOnlyClient:
    """Exposes only GET and HEAD, so a live test cannot fire a state-changing request."""

    def __init__(self, client: TestClient):
        self.get = client.get
        self.head = client.head


@pytest.fixture(scope="module")
def live():
    settings = Settings.from_env()
    missing = [persona for persona in ("owner", "requester") if persona not in settings.tokens]
    assert not missing, f"no token configured for persona(s) {missing}: check the repo-root .env"
    # Real transport; no JSONL file, so smoke runs do not pollute the recordings.
    app = create_app(dataclasses.replace(settings, log_file=None))
    with TestClient(app, follow_redirects=False) as client:
        yield ReadOnlyClient(client)


def test_whoami_owner(live):
    response = live.get("/api/whoami-v2", headers=OWNER)
    assert response.status_code == 200
    assert response.json()["name"] == "OwnerOfTheGatedModel"


def test_whoami_requester(live):
    response = live.get("/api/whoami-v2", headers=REQUESTER)
    assert response.status_code == 200
    assert response.json()["name"] == "TestingBOrig"


def test_owner_lists_pending_requests(live):
    response = live.get(f"/api/models/{REPO}/user-access-request/pending", headers=OWNER)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_requester_auth_check_is_gated(live):
    response = live.get(f"/api/models/{REPO}/auth-check", headers=REQUESTER)
    assert response.status_code == 403
    assert response.headers["x-error-code"] == "GatedRepo"


def test_anonymous_resolve_gated_file(live):
    response = live.get(f"/{REPO}/resolve/main/.gitattributes")
    assert response.status_code == 401
    assert response.headers["x-error-code"] == "GatedRepo"


def test_anonymous_resolve_allowlisted_file(live):
    response = live.get(f"/{REPO}/resolve/main/README.md")
    assert response.status_code == 200
