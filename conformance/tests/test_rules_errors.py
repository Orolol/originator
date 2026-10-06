"""Owner-endpoint error semantics and settings (api.md §3.3 "Check order", REV-12, CFG-2/3/7)."""

from __future__ import annotations

import pytest

from conformance import expect as E
from conformance.rule_seeds import CAROL, MANUAL, MISSING, OWNER, PUBLIC, REQUESTER, pending, rules_seed

OWNER_CALLS = [
    ("GET", "/api/models/{repo}/user-access-request/pending", None),
    ("POST", "/api/models/{repo}/user-access-request/handle", {"user": REQUESTER, "status": "accepted"}),
    ("POST", "/api/models/{repo}/user-access-request/grant", {"user": CAROL}),
    ("POST", "/api/models/{repo}/user-access-request/batch", {"status": "accepted", "requests": [{"user": REQUESTER}]}),
    ("PUT", "/api/models/{repo}/settings", {"gated": "auto"}),
]


@pytest.fixture
def seeded(be):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z")]))
    return be


@pytest.mark.parametrize("method,path,body", OWNER_CALLS)
@pytest.mark.parametrize("persona", ["anonymous", "bad"])
def test_check_order_authentication_is_401(seeded, method, path, body, persona):
    # api.md check order: anonymous or invalid token -> 401 + WWW-Authenticate, no X-Error-Code [OBS]
    response = seeded.req(persona, method, path.format(repo=MANUAL), body)
    E.assert_error(response, 401, E.INVALID_CREDENTIALS, www_authenticate=True)


@pytest.mark.parametrize("method,path,body", OWNER_CALLS)
def test_check_order_permission_is_403(seeded, method, path, body):
    # REV-12 / api.md: a non-owner gets 403 (no X-Error-Code), even on a non-gated repo
    for repo in (MANUAL, PUBLIC):
        response = seeded.req("requester", method, path.format(repo=repo), body)
        E.assert_error(response, 403, E.NO_PERMISSION)


def test_check_order_permission_before_validation(seeded):
    # api.md: permission is checked before body validation
    response = seeded.handle(MANUAL, {"user": REQUESTER, "status": "bogus"}, persona="requester")
    E.assert_error(response, 403, E.NO_PERMISSION)


@pytest.mark.parametrize("persona,status,message,code", [
    ("owner", 404, E.REPO_NOT_FOUND, "RepoNotFound"),  # [OBS] owner-unknown-repo-list
    ("anonymous", 401, E.INVALID_CREDENTIALS, None),  # api.md: anonymous gets 401 for an unknown repo
    ("requester", 404, E.REPO_NOT_FOUND, "RepoNotFound"),  # check order: unknown repo comes first
])
def test_check_order_unknown_repo_first(seeded, persona, status, message, code):
    response = seeded.list_requests(MISSING, "pending", persona=persona)
    E.assert_error(response, status, message, code=code)


@pytest.mark.parametrize("body,message,path", [
    ({"user": REQUESTER, "status": "bogus"},
     'Invalid option: expected one of "accepted"|"rejected"|"pending"|"reset"', "status"),  # [OBS] s7
    ({"user": REQUESTER, "status": "rejected", "rejectionReason": "x" * 201},
     "Too big: expected string to have <=200 characters", "rejectionReason"),  # [OBS] s7, REV-2
    ({"status": "pending"}, "Either userId or user must be provided, but not both", None),  # [OBS] s7, REV-5
])
def test_REV_12_validation_messages(seeded, body, message, path):
    E.assert_error(seeded.handle(MANUAL, body), 400, E.zod(message, path), body="zod")


def test_REV_12_unknown_user_and_missing_request(seeded):
    E.assert_error(seeded.handle(MANUAL, {"user": "this-user-does-not-exist-xyz-123", "status": "accepted"}), 404,
                   E.USER_NOT_FOUND)
    E.assert_error(seeded.handle(MANUAL, {"user": CAROL, "status": "accepted"}), 404, E.NO_REQUEST)


# --- settings -----------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["auto", "manual", False])
def test_CFG_2_CFG_3_settings_echo_gated_and_model_info_follows(be, value):
    be.put_state(rules_seed())
    response = be.settings(MANUAL, {"gated": value})
    E.assert_ok(response)
    assert response.json() == {"gated": value}  # CFG-3 [OBS]: echoes only the fields sent
    info = be.get("anonymous", f"/api/models/{MANUAL}?expand[]=gated")
    assert info.json()["gated"] == value


@pytest.mark.parametrize("value", [True, "public"])
def test_CFG_2_invalid_gated_value_is_400(be, value):
    be.put_state(rules_seed())
    response = be.settings(MANUAL, {"gated": value})
    assert response.status_code == 400, E.describe(response)  # SPEC: only false | "auto" | "manual"
    assert "x-error-code" not in response.headers
    assert be.get("anonymous", f"/api/models/{MANUAL}?expand[]=gated").json()["gated"] == "manual"


def test_CFG_3_empty_settings_payload_is_accepted(be):
    be.put_state(rules_seed())
    response = be.settings(MANUAL, {})
    E.assert_ok(response)
    assert response.json() == {}  # [OBS]


def test_CFG_3_no_get_settings(be):
    be.put_state(rules_seed())
    response = be.get("owner", f"/api/models/{MANUAL}/settings")
    E.assert_error(response, 404, E.NOT_FOUND_PAGE)  # [OBS] owner-get-settings


@pytest.mark.parametrize("body", [{"gatedNotificationsMode": "real-time"}, {"gatedNotificationsMode": "bulk"}])
def test_CFG_7_notification_mode_not_echoed(be, body):
    be.put_state(rules_seed())
    response = be.settings(MANUAL, body)
    E.assert_ok(response)
    assert response.json() == {}  # CFG-7 [OBS UI #245-246]


def test_CFG_3_notification_settings_not_in_model_info(be):
    be.put_state(rules_seed())
    E.assert_ok(be.settings(MANUAL, {"gatedNotificationsMode": "real-time"}))
    for query in ("", "?expand[]=gated&expand[]=cardData"):
        info = be.get("owner", f"/api/models/{MANUAL}{query}").json()
        assert not {"gatedNotificationsMode", "gatedNotificationsEmail"} & set(info), info


def test_whoami_personas(be):
    be.put_state(rules_seed())
    for persona, name in (("owner", OWNER), ("requester", REQUESTER), ("carol", CAROL)):
        response = be.get(persona, "/api/whoami-v2")
        E.assert_ok(response)
        assert response.json()["name"] == name
        assert response.json()["type"] == "user"
    for persona in ("anonymous", "bad"):
        E.assert_error(be.get(persona, "/api/whoami-v2"), 401, E.INVALID_CREDENTIALS, www_authenticate=True)
