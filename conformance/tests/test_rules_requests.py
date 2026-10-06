"""Request lifecycle rules, beyond what the recordings replay (behaviour.md §1, §4, §5, §6)."""

from __future__ import annotations

import pytest

from conformance import expect as E
from conformance.compare import Context, TimestampTracker, _norm_origin_url
from conformance.config import RECORDED_ORIGINS
from conformance.rule_seeds import (AUTO, AUTO_FIELDS, CAROL, FORM, FORM_ANSWERS, MANUAL, OWNER, PUBLIC, REQUESTER,
                                    pending, rules_seed)
from conformance.seeds import request

STATUSES = ("pending", "accepted", "rejected", "reset")


def lists(be, repo: str) -> dict[str, list[dict]]:
    result = {}
    for status in STATUSES:
        response = be.list_requests(repo, status)
        E.assert_ok(response)
        result[status] = response.json()
    return result


def where(be, repo: str, user: str) -> list[tuple[str, dict]]:
    return [(status, item) for status, items in lists(be, repo).items() for item in items if item["user"]["user"] == user]


def origin_free(be, url: str) -> str:
    return _norm_origin_url(url, Context(TimestampTracker(set()), be.base_url, RECORDED_ORIGINS))


def test_auto_mode_ask_access_is_accepted_immediately(be):
    # behaviour.md §4: no request + submit, auto -> accepted (immediately) [DOC]
    be.put_state(rules_seed())
    response = be.ask(AUTO, body={label: "on" for label in AUTO_FIELDS})
    assert response.status_code == 303, E.describe(response)
    assert origin_free(be, response.headers["location"]) == f"<origin>/{AUTO}"  # REQ-2: absolute, repo page
    check = be.auth_check(AUTO, "requester")
    E.assert_ok(check)
    assert check.text == "OK"
    E.assert_ok(be.resolve(AUTO, "config.json", "requester"))
    found = where(be, AUTO, REQUESTER)
    assert [status for status, _ in found] == ["accepted"], found
    item = found[0][1]
    assert item["status"] == "accepted"
    assert "email" in item["user"]  # REQ-3: self-service requests share the e-mail
    assert "timestamp" in item  # SPEC: required


def test_manual_mode_ask_access_is_pending_with_303(be):
    be.put_state(rules_seed())
    response = be.ask(MANUAL)
    assert response.status_code == 303, E.describe(response)
    assert "x-error-code" not in response.headers and "x-error-message" not in response.headers  # REQ-2
    assert origin_free(be, response.headers["location"]) == f"<origin>/{MANUAL}"
    assert E.media(response) == "text/plain"
    from conformance.compare import _norm_redirect_text
    ctx = Context(TimestampTracker(set()), be.base_url, RECORDED_ORIGINS)
    assert _norm_redirect_text(response.text, ctx) == f"See Other. Redirecting to <origin>/{MANUAL}"  # api.md §3.3
    found = where(be, MANUAL, REQUESTER)
    assert [status for status, _ in found] == ["pending"]
    assert list(found[0][1]) == ["user", "timestamp", "status"]  # REQ-6: pending item, no extra fields


@pytest.mark.parametrize("encoding", ["json", "form"])
def test_form_fields_are_stored_with_labels_as_keys(be, encoding):
    # gate-form.md §1-2 / SPEC: fields = {label: string}; REQ-2: JSON and form bodies behave the same
    be.put_state(rules_seed())
    response = be.ask(FORM, body=FORM_ANSWERS, encoding=encoding)
    assert response.status_code == 303, E.describe(response)
    found = where(be, FORM, REQUESTER)
    assert [status for status, _ in found] == ["pending"], found
    fields = found[0][1].get("fields")
    assert fields == FORM_ANSWERS, found[0][1]
    assert all(isinstance(value, str) for value in fields.values())


def test_REV_4_cancel_in_auto_mode_goes_back_to_pending(be):
    # client tests (TestAccessRequestAPI): grant -> cancel puts the user in pending even when gated == "auto"
    be.put_state(rules_seed())
    E.assert_ok(be.grant(AUTO, {"user": CAROL}))
    E.assert_ok(be.handle(AUTO, {"user": CAROL, "status": "pending"}))
    found = where(be, AUTO, CAROL)
    assert [status for status, _ in found] == ["pending"], found
    assert "reviewedAt" not in found[0][1]  # TS-2: removed when back to pending


def test_REV_6_REQ_5_grant_without_request(be):
    be.put_state(rules_seed())
    response = be.grant(MANUAL, {"user": CAROL})
    E.assert_ok(response)
    assert response.json() == {}  # [OBS] grant success body
    found = where(be, MANUAL, CAROL)
    assert [status for status, _ in found] == ["accepted"], found
    item = found[0][1]
    assert item["user"].get("email") is None, item  # REQ-5: e-mail not shared when granted manually
    assert item["grantedBy"]["user"] == OWNER  # Q-10 partial [OBS]: grantedBy = the granting owner
    assert list(item["grantedBy"]) == ["_id", "avatarUrl", "isPro", "fullname", "user", "type"]  # [OBS] shape
    assert "reviewedAt" in item and "timestamp" in item  # TS-2 / SPEC required
    check = be.auth_check(MANUAL, "carol")
    E.assert_ok(check)


def test_REV_7_grant_when_user_already_has_access(be):
    be.put_state(rules_seed())
    E.assert_ok(be.grant(MANUAL, {"user": CAROL}))
    E.assert_error(be.grant(MANUAL, {"user": CAROL}), 400, E.ALREADY_HAS_ACCESS)  # [OBS] s6-grant-again


def test_REV_7_grant_unknown_user_is_404(be):
    be.put_state(rules_seed())
    response = be.grant(MANUAL, {"user": "this-user-does-not-exist-xyz-123"})
    assert response.status_code == 404, E.describe(response)  # REV-7 [CLIENT doc]


def test_REV_7_grant_on_non_gated_repo_is_400(be):
    # REV-7 "Repo not gated -> 400" [CLIENT doc]. Caveat: CFG-6 [OBS] shows the same docstring is wrong for
    # the list endpoint once requests exist; grant on a non-gated repo has not been recorded.
    be.put_state(rules_seed())
    response = be.grant(PUBLIC, {"user": CAROL})
    assert response.status_code == 400, E.describe(response)


@pytest.mark.parametrize("start,target", [
    ("accepted", "rejected"),  # [CLIENT tests]
    ("rejected", "pending"),  # [CLIENT doc]
    ("accepted", "reset"),  # [OBS W s5]
    ("rejected", "reset"),  # [OBS C m8]
    ("rejected", "accepted"),  # [OBS W s4]
    ("pending", "rejected"),  # [OBS C m5]
])
def test_REV_handle_allowed_transitions(be, start, target):
    reviewed = None if start == "pending" else "2026-10-05T14:10:00.000Z"
    granted = OWNER if start == "accepted" else None
    be.put_state(rules_seed([request(REQUESTER, start, "2026-10-05T14:00:00.000Z", reviewed, granted, repo=MANUAL)]))
    response = be.handle(MANUAL, {"user": REQUESTER, "status": target})
    E.assert_ok(response)
    assert response.json() == {}
    found = where(be, MANUAL, REQUESTER)
    assert [status for status, _ in found] == [target], found
    item = found[0][1]
    assert item["timestamp"] == "2026-10-05T14:00:00.000Z"  # TS-1: never changed by a review
    if target == "pending":
        assert "reviewedAt" not in item  # TS-2
    else:
        assert item["reviewedAt"] > (reviewed or item["timestamp"])  # TS-2: time of the last review
    assert ("grantedBy" in item) == (target == "accepted")  # Q-10 partial [OBS]: only accepted entries


@pytest.mark.parametrize("status", ["accepted", "rejected", "pending"])
def test_REV_1_same_status_is_404(be, status):
    reviewed = None if status == "pending" else "2026-10-05T14:10:00.000Z"
    be.put_state(rules_seed([request(REQUESTER, status, "2026-10-05T14:00:00.000Z", reviewed,
                                     OWNER if status == "accepted" else None, repo=MANUAL)]))
    E.assert_error(be.handle(MANUAL, {"user": REQUESTER, "status": status}), 404, E.NO_REQUEST)


def test_REQ_4_reasons_never_listed_nor_told_to_requester(be):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z")]))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "rejected", "rejectionReason": "R" * 200}))  # REV-2: 200 ok
    status, item = where(be, MANUAL, REQUESTER)[0]
    assert status == "rejected" and "rejectionReason" not in item
    E.assert_error(be.auth_check(MANUAL, "requester"), 403, E.gate_rejected(MANUAL), code="GatedRepo")
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "reset", "resetReason": "S" * 200}))
    status, item = where(be, MANUAL, REQUESTER)[0]
    assert status == "reset" and "resetReason" not in item
    E.assert_error(be.auth_check(MANUAL, "requester"), 403, E.gate_reset(MANUAL), code="GatedRepo")


@pytest.mark.parametrize("body", [
    {"user": REQUESTER, "status": "reset", "resetReason": "x" * 201},  # REV-3: at most 200
    {"user": REQUESTER, "userId": "6ac3a4b8792f9017b6cb67ec", "status": "accepted"},  # REV-5: not both
    {"user": REQUESTER},  # SPEC: status required
])
def test_REV_handle_validation_is_400_without_code(be, body):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z")]))
    response = be.handle(MANUAL, body)
    assert response.status_code == 400, E.describe(response)
    assert "x-error-code" not in response.headers  # REV-12
    error = response.json()["error"]
    assert error.startswith("✖ "), error  # zod pretty format (api.md)
    assert response.headers["x-error-message"] == E.ascii_header(error)  # api.md: ASCII-sanitised copy


def test_REV_9_batch_outcomes_in_input_order(be):
    be.put_state(rules_seed([
        pending(REQUESTER, "2026-10-05T14:00:00.000Z"),
        pending("conf-user-01", "2026-10-05T14:01:00.000Z"),
        request("conf-user-02", "accepted", "2026-10-05T14:02:00.000Z", "2026-10-05T14:03:00.000Z", OWNER, repo=MANUAL),
    ], users=2))
    requester_id = next(u["_id"] for u in rules_seed()["users"] if u["user"] == REQUESTER)
    body = {"status": "accepted", "requests": [
        {"user": "conf-user-02"}, {"user": "this-user-does-not-exist-xyz-123"}, {"user": CAROL},
        {"userId": requester_id}, {"user": "conf-user-01"},
    ]}
    response = be.batch(MANUAL, body)
    E.assert_ok(response)
    assert response.json() == [
        {"user": "conf-user-02", "ok": True},  # already in the target status -> ok (REV-9 [OBS])
        {"user": "this-user-does-not-exist-xyz-123", "ok": False, "error": "user_not_found"},  # [OBS]
        {"user": CAROL, "ok": False, "error": "request_not_found"},  # SPEC error enum
        {"userId": requester_id, "ok": True},  # SPEC: echoes userId when sent
        {"user": "conf-user-01", "ok": True},
    ], response.text
    assert [list(item) for item in response.json()[:2]] == [["user", "ok"], ["user", "ok", "error"]]  # [OBS] order
    accepted = {item["user"]["user"] for item in lists(be, MANUAL)["accepted"]}
    assert accepted == {REQUESTER, "conf-user-01", "conf-user-02"}


def test_REV_9_batch_back_to_pending_removes_reviewedAt(be):
    be.put_state(rules_seed([request(REQUESTER, "rejected", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                                     repo=MANUAL)]))
    E.assert_ok(be.batch(MANUAL, {"status": "pending", "requests": [{"user": REQUESTER}]}))
    status, item = where(be, MANUAL, REQUESTER)[0]
    assert status == "pending" and "reviewedAt" not in item  # TS-2
    assert item["timestamp"] == "2026-10-05T14:00:00.000Z"  # TS-1


@pytest.mark.parametrize("count", [0, 101])
def test_REV_9_batch_size_limits(be, count):
    # SPEC: requests 1-100
    be.put_state(rules_seed())
    response = be.batch(MANUAL, {"status": "accepted", "requests": [{"user": CAROL}] * count})
    assert response.status_code == 400, E.describe(response)
    assert "x-error-code" not in response.headers
    assert response.headers["x-error-message"] == E.ascii_header(response.json()["error"])


def test_reset_then_resubmit_creates_a_new_pending_request(be):
    # behaviour.md §4 [OBS W s5b]: new timestamp, reviewedAt removed, gone from the reset list
    be.put_state(rules_seed([request(REQUESTER, "reset", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                                     repo=MANUAL)]))
    assert be.ask(MANUAL).status_code == 303
    found = where(be, MANUAL, REQUESTER)
    assert [status for status, _ in found] == ["pending"], found
    item = found[0][1]
    assert item["timestamp"] > "2026-10-05T14:05:00.000Z" and "reviewedAt" not in item


def test_rejected_resubmit_is_silently_ignored(be):
    # behaviour.md §4 [OBS C m7]: 303, still rejected, same reviewedAt
    be.put_state(rules_seed([request(REQUESTER, "rejected", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                                     repo=MANUAL)]))
    assert be.ask(MANUAL).status_code == 303
    found = where(be, MANUAL, REQUESTER)
    assert [(s, i["timestamp"], i["reviewedAt"]) for s, i in found] == [
        ("rejected", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z")]


# --- REQ-7: requester self-cancel [OBS 2026-10-06, requester-cancel X c1-c6, ui-walkthrough #320] --------

def report_users(be, repo: str) -> list[str]:
    response = be.report(repo)
    E.assert_ok(response)
    return [entry["user"] for entry in response.json()]


def test_REQ_7_self_cancel_deletes_a_pending_request(be):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-06T14:00:00.000Z")]))
    response = be.cancel(MANUAL)
    E.assert_ok(response)  # X c2-cancel-pending: 200, no X-Error-*
    assert E.media(response) == "application/json"
    assert response.json() == {"ok": True}
    assert lists(be, MANUAL) == {status: [] for status in STATUSES}  # X c2b: gone from the four lists
    assert report_users(be, MANUAL) == []  # X c2b-report: gone from the report
    E.assert_error(be.auth_check(MANUAL, "requester"), 403, E.gate_no_request(MANUAL), code="GatedRepo")  # X c2b
    E.assert_error(be.resolve(MANUAL, "config.json", "requester"), 403, E.gate_no_request(MANUAL), code="GatedRepo",
                   body="text")
    # a new ask-access then creates a new pending request (X c3-ask, UI #324)
    assert be.ask(MANUAL).status_code == 303
    found = where(be, MANUAL, REQUESTER)
    assert [status for status, _ in found] == ["pending"], found
    assert found[0][1]["timestamp"] > "2026-10-06T14:00:00.000Z"  # TS-1: a new submission


@pytest.mark.parametrize("state", ["accepted", "rejected", "reset", None])
def test_REQ_7_self_cancel_without_a_pending_request_is_404_and_changes_nothing(be, state):
    # X c3-cancel-accepted, c4-cancel-rejected, c1-cancel-reset, c2-cancel-again (no request)
    seeded = []
    if state:
        seeded = [request(REQUESTER, state, "2026-10-06T14:00:00.000Z", "2026-10-06T14:05:00.000Z",
                          OWNER if state == "accepted" else None, repo=MANUAL)]
    be.put_state(rules_seed(seeded))
    before = (lists(be, MANUAL), be.report(MANUAL).json(), be.auth_check(MANUAL, "requester").text)
    E.assert_error(be.cancel(MANUAL), 404, E.NO_PENDING_REQUEST)  # JSON {"error"}, same X-Error-Message, no code
    after = (lists(be, MANUAL), be.report(MANUAL).json(), be.auth_check(MANUAL, "requester").text)
    assert after == before


def test_REQ_7_rejected_user_cannot_clear_the_rejection(be):
    # X c4-cancel-rejected then c5-ask-after-reject-cancel: still rejected, same reviewedAt
    be.put_state(rules_seed([request(REQUESTER, "rejected", "2026-10-06T14:00:00.000Z", "2026-10-06T14:05:00.000Z",
                                     repo=MANUAL)]))
    E.assert_error(be.cancel(MANUAL), 404, E.NO_PENDING_REQUEST)
    assert be.ask(MANUAL).status_code == 303
    found = where(be, MANUAL, REQUESTER)
    assert [(s, i["timestamp"], i["reviewedAt"]) for s, i in found] == [
        ("rejected", "2026-10-06T14:00:00.000Z", "2026-10-06T14:05:00.000Z")]
    E.assert_error(be.auth_check(MANUAL, "requester"), 403, E.gate_rejected(MANUAL), code="GatedRepo")


def test_REQ_7_owner_self_cancel_on_own_repo_is_404(be):
    # X c6-owner-cancel (the requester's rejected request stays untouched)
    be.put_state(rules_seed([request(REQUESTER, "rejected", "2026-10-06T14:00:00.000Z", "2026-10-06T14:05:00.000Z",
                                     repo=MANUAL)]))
    E.assert_error(be.cancel(MANUAL, persona="owner"), 404, E.NO_PENDING_REQUEST)
    assert [status for status, _ in where(be, MANUAL, REQUESTER)] == ["rejected"]


def test_REQ_7_only_the_callers_own_request_is_cancelled(be):
    # REQ-7: "only withdraws a pending request" of the caller (the endpoint takes no body)
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-06T14:00:00.000Z"), pending(CAROL, "2026-10-06T14:01:00.000Z")]))
    E.assert_ok(be.cancel(MANUAL))
    assert [i["user"]["user"] for i in lists(be, MANUAL)["pending"]] == [CAROL]


def test_REQ_7_anonymous_self_cancel_is_401(be):
    # X c6-anon-cancel: 401 "Invalid username or password." with WWW-Authenticate, no X-Error-Code
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-06T14:00:00.000Z")]))
    E.assert_error(be.cancel(MANUAL, persona="anonymous"), 401, E.INVALID_CREDENTIALS, www_authenticate=True)
    assert [status for status, _ in where(be, MANUAL, REQUESTER)] == ["pending"]
