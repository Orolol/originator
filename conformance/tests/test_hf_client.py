"""The official `huggingface_hub` client, unchanged, against the backend.

conftest.py pins HF_ENDPOINT before this module imports huggingface_hub: the access-request methods
build their URLs from `constants.ENDPOINT`, not from `HfApi(endpoint=...)` (client-library.md, api.md §4).
The flow mirrors the client's own integration test `tests/test_hf_api.py::TestAccessRequestAPI`
(client-library.md §3), on our auto-gated demo repo with DemoCarol as the second user.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from huggingface_hub import HfApi, constants, hf_hub_download
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

from conformance.config import backend_url
from conformance.rule_seeds import AUTO, CAROL, FORM, FORM_ANSWERS, MANUAL, REQUESTER, pending, rules_seed, text_file


@pytest.fixture
def api(be):
    be.put_state(rules_seed())
    return HfApi(endpoint=be.base_url, token="persona-owner")


def test_client_endpoint_is_pinned_to_backend():
    assert constants.ENDPOINT == backend_url()


def test_access_request_api_flow(api):
    # 1. a fresh gated repo has all three lists empty
    assert list(api.list_pending_access_requests(AUTO)) == []
    assert list(api.list_accepted_access_requests(AUTO)) == []
    assert list(api.list_rejected_access_requests(AUTO)) == []
    # 2. grant -> accepted, e-mail not shared when granted manually
    api.grant_access(AUTO, CAROL)
    accepted = list(api.list_accepted_access_requests(AUTO))
    assert len(accepted) == 1
    assert accepted[0].username == CAROL and accepted[0].status == "accepted"
    assert accepted[0].email is None
    assert isinstance(accepted[0].timestamp, datetime)
    # 3. cancel -> pending, even in auto mode
    api.cancel_access_request(AUTO, CAROL)
    assert list(api.list_accepted_access_requests(AUTO)) == []
    assert [r.username for r in api.list_pending_access_requests(AUTO)] == [CAROL]
    # 4. reject with a reason
    api.reject_access_request(AUTO, CAROL, rejection_reason="Not this time")
    assert list(api.list_pending_access_requests(AUTO)) == []
    assert [r.username for r in api.list_rejected_access_requests(AUTO)] == [CAROL]
    # 5. rejected -> accepted is allowed
    api.accept_access_request(AUTO, CAROL)
    assert [r.username for r in api.list_accepted_access_requests(AUTO)] == [CAROL]


def test_access_request_api_same_status_errors(api):
    api.grant_access(AUTO, CAROL)
    with pytest.raises(HfHubHTTPError):
        api.grant_access(AUTO, CAROL)
    with pytest.raises(HfHubHTTPError):
        api.accept_access_request(AUTO, CAROL)
    api.reject_access_request(AUTO, CAROL, rejection_reason=None)
    with pytest.raises(HfHubHTTPError):
        api.reject_access_request(AUTO, CAROL, rejection_reason=None)
    api.cancel_access_request(AUTO, CAROL)
    with pytest.raises(HfHubHTTPError):
        api.cancel_access_request(AUTO, CAROL)


def test_auth_check_raises_gated_repo_error_for_requester(api):
    with pytest.raises(GatedRepoError):
        api.auth_check(AUTO, token="persona-requester")
    with pytest.raises(GatedRepoError):
        api.auth_check(MANUAL, token="persona-requester")
    api.auth_check(MANUAL)  # the owner passes (ACC-1)


def test_list_parses_self_service_request_with_fields(be):
    be.put_state(rules_seed())
    assert be.ask(FORM, body=FORM_ANSWERS).status_code == 303
    api = HfApi(endpoint=be.base_url, token="persona-owner")
    [item] = list(api.list_pending_access_requests(FORM))
    assert (item.username, item.fullname, item.status) == (REQUESTER, "Bridge", "pending")
    assert item.email is not None and "@" in item.email
    assert item.fields == FORM_ANSWERS
    assert isinstance(item.timestamp, datetime)


def test_list_many_requests(be):
    be.put_state(rules_seed([pending(f"conf-user-{i:02d}", f"2026-10-05T10:{i:02d}:00.000Z") for i in range(1, 26)],
                            users=25))
    api = HfApi(endpoint=be.base_url, token="persona-owner")
    assert len(list(api.list_pending_access_requests(MANUAL))) == 25


@pytest.mark.parametrize("value", ["manual", False, "auto"])
def test_update_repo_settings_round_trips_through_model_info(api, value):
    api.update_repo_settings(AUTO, gated=value)
    assert api.model_info(AUTO).gated == value


def test_hf_hub_download_follows_the_gate(be, tmp_path):
    be.put_state(rules_seed())
    readme = hf_hub_download(MANUAL, "README.md", cache_dir=tmp_path / "anon", token=False)  # ACC-5 allowlist
    assert open(readme, "rb").read() == text_file("README.md")["text"].encode()
    with pytest.raises(GatedRepoError):
        hf_hub_download(MANUAL, "config.json", cache_dir=tmp_path / "anon", token=False)
    with pytest.raises(GatedRepoError):
        hf_hub_download(MANUAL, "config.json", cache_dir=tmp_path / "req", token="persona-requester")
    owned = hf_hub_download(MANUAL, "config.json", cache_dir=tmp_path / "owner", token="persona-owner")
    assert open(owned, "rb").read() == text_file("config.json")["text"].encode()
