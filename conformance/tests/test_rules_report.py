"""Access report (REP-1, REP-2)."""

from __future__ import annotations

from conformance import expect as E
from conformance.rule_seeds import CAROL, MANUAL, OWNER, REQUESTER, pending, rules_seed
from conformance.seeds import recorded_whoami, request


def four_statuses_seed():
    return rules_seed([
        pending(REQUESTER, "2026-10-05T14:00:00.000Z"),
        request(CAROL, "accepted", "2026-10-05T14:01:00.000Z", "2026-10-05T14:11:00.000Z", OWNER, repo=MANUAL),
        request("conf-user-01", "rejected", "2026-10-05T14:02:00.000Z", "2026-10-05T14:12:00.000Z", repo=MANUAL),
        request("conf-user-02", "reset", "2026-10-05T14:03:00.000Z", "2026-10-05T14:13:00.000Z", repo=MANUAL),
    ], users=2)


def test_REP_1_headers_and_every_status(be):
    be.put_state(four_statuses_seed())
    response = be.report(MANUAL)
    E.assert_ok(response)
    # [OBS] owner-reads: application/json without charset, attachment filename
    assert response.headers["content-type"] == "application/json", E.describe(response)
    assert response.headers["content-disposition"] == f"attachment; filename=user-access-report-{OWNER}-conf-manual.json"
    entries = {entry["user"]: entry for entry in response.json()}
    assert set(entries) == {REQUESTER, CAROL, "conf-user-01", "conf-user-02"}  # REP-1: every request, every status
    assert {entry["status"] for entry in entries.values()} == {"pending", "accepted", "rejected", "reset"}


def test_REP_1_entry_contents(be):
    be.put_state(four_statuses_seed())
    entries = {entry["user"]: entry for entry in be.report(MANUAL).json()}
    # pending entry: exactly these keys in this order [OBS owner-reads, owner-walkthrough s11]
    assert list(entries[REQUESTER]) == ["fullname", "user", "email", "time", "status"]
    assert entries[REQUESTER]["fullname"] == "Bridge"
    assert entries[REQUESTER]["time"] == "2026-10-05T14:00:00.000Z"  # time = initial request
    # reviewed entries carry reviewedAt [DOC]; key position is open for rejected/reset (Q-14), so only the value
    # is checked here (accepted: test_REP_1_accepted_entry_key_order_and_grantedBy)
    for user, reviewed in ((CAROL, "2026-10-05T14:11:00.000Z"), ("conf-user-01", "2026-10-05T14:12:00.000Z"),
                           ("conf-user-02", "2026-10-05T14:13:00.000Z")):
        assert entries[user].get("reviewedAt") == reviewed, entries[user]
        assert {"fullname", "user", "email", "time", "status"} <= set(entries[user])
    assert "rejectionReason" not in entries["conf-user-01"]  # Q-19 partial [OBS]: reason absent from the report


def test_REP_1_accepted_entry_key_order_and_grantedBy(be):
    # [OBS 2026-10-06, owner-walkthrough s1-report]: an accepted entry is {fullname, user, email, time, reviewedAt,
    # status, grantedBy: {fullname, user}} in that order; time = the initial request, kept by the review (TS-1)
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-06T14:00:00.000Z")]))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "accepted"}))
    [entry] = be.report(MANUAL).json()
    assert list(entry) == ["fullname", "user", "email", "time", "reviewedAt", "status", "grantedBy"], entry
    assert (entry["fullname"], entry["user"], entry["status"]) == ("Bridge", REQUESTER, "accepted")
    assert entry["time"] == "2026-10-06T14:00:00.000Z"
    assert entry["reviewedAt"] > entry["time"]  # TS-2: time of the accept
    assert "@" in entry["email"]  # the requester's own request shares the e-mail (REQ-3)
    owner_fullname = recorded_whoami("owner")["fullname"]
    assert list(entry["grantedBy"]) == ["fullname", "user"]
    assert entry["grantedBy"] == {"fullname": owner_fullname, "user": OWNER}


def test_REP_1_self_cancelled_request_is_gone_from_the_report(be):
    # REP-1 / REQ-7 [OBS 2026-10-06, requester-cancel c2b-report: []]
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-06T14:00:00.000Z")]))
    E.assert_ok(be.cancel(MANUAL))
    assert be.report(MANUAL).json() == []


def test_REP_2_report_needs_authentication(be):
    be.put_state(four_statuses_seed())
    response = be.report(MANUAL, persona="anonymous")
    assert response.status_code == 401, E.describe(response)  # [OBS] report-anon
    assert response.headers.get("x-error-message") == E.INVALID_CREDENTIALS
    assert "x-error-code" not in response.headers
    assert response.headers.get("www-authenticate") == E.WWW_AUTHENTICATE
