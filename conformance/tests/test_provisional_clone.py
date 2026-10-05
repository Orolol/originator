"""PROVISIONAL choices, not observed HF behaviour.

Each test checks a choice the KB records as provisional until a question is answered on the real Hub.
A failure here means the clone departs from its own documented provisional choice, not that it departs
from HF. When a question is resolved, move the test to a test_rules_* module or rewrite it.

Sources (read as text; expectations are written from these sentences, not from the clone's code):
- docs/hf-gated/open-questions.md, "Provisional choices in the clone (2026-10-05)" (table rows cited
  by their Q-id below);
- docs/system.md "Determinism" (list order) and "Outbox entry" (only §7 effects);
- docs/hf-gated/api.md §3.3 "Check order" (validation, then unknown user, then request lookup).
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from conformance import expect as E
from conformance.rule_seeds import (AUTO, AUTO_FIELDS, CAROL, FORM, FORM_ANSWERS, MANUAL, OWNER, PUBLIC, REQUESTER,
                                    demo_repo, pending, rules_seed)
from conformance.seeds import request

pytestmark = pytest.mark.provisional

STATUSES = ("pending", "accepted", "rejected", "reset")
BAD_STATUS = 'Invalid option: expected one of "accepted"|"rejected"|"pending"|"reset"'


def all_lists(be, repo: str) -> dict[str, list[str]]:
    return {s: [i["user"]["user"] for i in be.list_requests(repo, s).json()] for s in STATUSES}


def only(be, repo: str, user: str) -> tuple[str, dict]:
    found = [(s, i) for s in STATUSES for i in be.list_requests(repo, s).json() if i["user"]["user"] == user]
    assert len(found) == 1, found
    return found[0]


def reviewed(user: str, status: str, repo: str = MANUAL, fields: dict | None = None) -> dict:
    return request(user, status, "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                   OWNER if status == "accepted" else None, fields=fields, repo=repo)


# --- system.md / api.md -----------------------------------------------------------------------------

def test_provisional_Q10_lists_ordered_by_timestamp_then_insertion(be):
    # inserted out of timestamp order; two share a timestamp (insertion order breaks the tie)
    be.put_state(rules_seed([
        pending("conf-user-03", "2026-10-05T12:00:00.000Z"),
        pending("conf-user-01", "2026-10-05T10:00:00.000Z"),
        pending("conf-user-04", "2026-10-05T11:00:00.000Z"),
        pending("conf-user-02", "2026-10-05T11:00:00.000Z"),
    ], users=4))
    users = [item["user"]["user"] for item in be.list_requests(MANUAL, "pending").json()]
    assert users == ["conf-user-01", "conf-user-04", "conf-user-02", "conf-user-03"]


@pytest.mark.parametrize("body,message", [
    ({"user": "this-user-does-not-exist-xyz-123", "status": "bogus"}, E.zod(BAD_STATUS, "status")),  # validation first
    ({"user": CAROL, "status": "bogus"}, E.zod(BAD_STATUS, "status")),  # before the request lookup
    # both identifiers: the same refinement as "neither" (its text says "but not both")
    ({"user": REQUESTER, "userId": "6ac3a4b8792f9017b6cb67ec", "status": "accepted"},
     E.zod("Either userId or user must be provided, but not both")),
    # reset reason: same zod rule as rejectionReason (REV-3: at most 200 characters)
    ({"user": REQUESTER, "status": "reset", "resetReason": "x" * 201},
     E.zod("Too big: expected string to have <=200 characters", "resetReason")),
])
def test_provisional_check_order_validation_first(be, body, message):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z")]))
    E.assert_error(be.handle(MANUAL, body), 400, message, body="zod")


def test_provisional_Q20_no_mail_for_reviews_and_grants(be):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z")]))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "accepted"}))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "rejected", "rejectionReason": "no"}))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "pending"}))
    E.assert_ok(be.grant(MANUAL, {"user": CAROL}))
    E.assert_ok(be.batch(MANUAL, {"status": "accepted", "requests": [{"user": REQUESTER}]}))
    assert be.outbox() == []


def test_provisional_Q20_ignored_resubmit_sends_nothing(be):
    be.put_state(rules_seed([reviewed(REQUESTER, "rejected")]))
    assert be.ask(MANUAL).status_code == 303
    assert be.outbox() == []


# --- open-questions.md "Provisional choices in the clone" --------------------------------------------

def test_provisional_Q1_anonymous_ask_access_is_401(be):
    be.put_state(rules_seed())
    response = be.ask(MANUAL, persona="anonymous")
    assert response.status_code == 401, E.describe(response)
    assert response.headers.get("x-error-message") == E.INVALID_CREDENTIALS
    assert E.media(response) == "text/html"  # "with an HTML body"
    assert all_lists(be, MANUAL) == {s: [] for s in STATUSES}


def test_provisional_Q2_resubmit_while_accepted_is_a_no_op(be):
    be.put_state(rules_seed([reviewed(REQUESTER, "accepted")]))
    assert be.ask(MANUAL).status_code == 303
    status, item = only(be, MANUAL, REQUESTER)
    assert (status, item["timestamp"], item["reviewedAt"]) == ("accepted", "2026-10-05T14:00:00.000Z",
                                                               "2026-10-05T14:05:00.000Z")


def test_provisional_Q2_resubmit_while_pending_keeps_timestamp_and_fields(be):
    be.put_state(rules_seed())
    assert be.ask(FORM, body=FORM_ANSWERS).status_code == 303
    first = only(be, FORM, REQUESTER)[1]
    assert be.ask(FORM, body={**FORM_ANSWERS, "Company": "Other Corp"}).status_code == 303
    status, again = only(be, FORM, REQUESTER)
    assert status == "pending"
    assert (again["timestamp"], again["fields"]) == (first["timestamp"], FORM_ANSWERS)


def test_provisional_Q2_ask_access_on_non_gated_repo_is_a_no_op(be):
    be.put_state(rules_seed())
    assert be.ask(PUBLIC).status_code == 303
    assert all_lists(be, PUBLIC) == {s: [] for s in STATUSES}


def test_provisional_Q2_resubmit_after_reset_replaces_fields(be):
    old = {**FORM_ANSWERS, "Company": "Old Corp"}
    be.put_state(rules_seed([reviewed(REQUESTER, "reset", repo=FORM, fields=old)]))
    assert be.ask(FORM, body=FORM_ANSWERS).status_code == 303
    status, item = only(be, FORM, REQUESTER)
    assert (status, item["fields"]) == ("pending", FORM_ANSWERS)


@pytest.mark.parametrize("status", STATUSES)
def test_provisional_Q3_self_cancel_deletes_the_request(be, status):
    seeded = pending(REQUESTER, "2026-10-05T14:00:00.000Z") if status == "pending" else reviewed(REQUESTER, status)
    be.put_state(rules_seed([seeded]))
    response = be.req("requester", "POST", f"/api/models/{MANUAL}/user-access-request/cancel")
    E.assert_ok(response)
    assert response.json() == {}
    assert all_lists(be, MANUAL) == {s: [] for s in STATUSES}
    E.assert_error(be.auth_check(MANUAL, "requester"), 403, E.gate_no_request(MANUAL), code="GatedRepo")
    again = be.req("requester", "POST", f"/api/models/{MANUAL}/user-access-request/cancel")
    E.assert_error(again, 404, E.NO_REQUEST)


@pytest.mark.parametrize("start,target", [("pending", "reset"), ("reset", "accepted"), ("reset", "rejected"),
                                          ("reset", "pending")])
def test_provisional_Q5_reset_transitions_allowed(be, start, target):
    seeded = pending(REQUESTER, "2026-10-05T14:00:00.000Z") if start == "pending" else reviewed(REQUESTER, start)
    be.put_state(rules_seed([seeded]))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": target}))
    assert only(be, MANUAL, REQUESTER)[0] == target


def test_provisional_Q5_reset_to_reset_is_404(be):
    be.put_state(rules_seed([reviewed(REQUESTER, "reset")]))
    E.assert_error(be.handle(MANUAL, {"user": REQUESTER, "status": "reset"}), 404, E.NO_REQUEST)


@pytest.mark.parametrize("status", ["rejected", "reset"])
def test_provisional_Q6_grant_accepts_rejected_and_reset_users(be, status):
    be.put_state(rules_seed([reviewed(REQUESTER, status)]))
    E.assert_ok(be.grant(MANUAL, {"user": REQUESTER}))
    found_status, item = only(be, MANUAL, REQUESTER)
    assert found_status == "accepted" and item["grantedBy"]["user"] == OWNER
    assert item["timestamp"] == "2026-10-05T14:00:00.000Z"  # "like a pending one" (REV-8: timestamp kept)


def test_provisional_Q6_self_grant_is_400(be):
    be.put_state(rules_seed())
    E.assert_error(be.grant(MANUAL, {"user": OWNER}), 400, E.ALREADY_HAS_ACCESS)


def test_provisional_Q9_no_not_gated_400_on_grant_and_handle(be):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z", repo=PUBLIC)]))
    E.assert_ok(be.grant(PUBLIC, {"user": CAROL}))
    E.assert_ok(be.handle(PUBLIC, {"user": REQUESTER, "status": "accepted"}))


def test_provisional_Q9_reason_with_other_status_is_ignored(be):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z")]))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "accepted", "rejectionReason": "ignored"}))
    assert only(be, MANUAL, REQUESTER)[0] == "accepted"


def _three_pending():
    return rules_seed([pending("conf-user-01", "2026-10-05T10:00:00.000Z"),
                       pending("conf-user-02", "2026-10-05T11:00:00.000Z"),
                       pending("conf-user-03", "2026-10-05T12:00:00.000Z")], users=3)


@pytest.mark.parametrize("query,expected", [
    ("?after=2026-10-05T10:00:00.000Z", ["conf-user-02", "conf-user-03"]),
    ("?before=2026-10-05T12:00:00.000Z", ["conf-user-01", "conf-user-02"]),
    ("?after=2026-10-05T10:00:00.000Z&before=2026-10-05T12:00:00.000Z", ["conf-user-02"]),
])
def test_provisional_Q10_after_before_filter_timestamp_exclusive(be, query, expected):
    be.put_state(_three_pending())
    response = be.list_requests(MANUAL, "pending", query)
    E.assert_ok(response)
    assert [i["user"]["user"] for i in response.json()] == expected


def test_provisional_Q10_next_link_uses_after_last_timestamp(be):
    be.put_state(rules_seed([pending(f"conf-user-{i:02d}", f"2026-10-05T10:{i:02d}:00.000Z") for i in range(1, 13)],
                            users=12))
    first = be.list_requests(MANUAL, "pending", "?limit=10")
    page = first.json()
    query = parse_qs(urlsplit(first.links["next"]["url"]).query)
    assert query["after"] == [page[-1]["timestamp"]], first.headers["link"]
    second = be.req("owner", "GET", first.links["next"]["url"][len(be.base_url):]).json()
    assert [i["user"]["user"] for i in page + second] == [f"conf-user-{i:02d}" for i in range(1, 13)]


def test_provisional_Q10_auto_accept_reviewedAt_equals_timestamp(be):
    be.put_state(rules_seed())
    assert be.ask(AUTO, body={label: "on" for label in AUTO_FIELDS}).status_code == 303
    status, item = only(be, AUTO, REQUESTER)
    assert status == "accepted"
    assert item["reviewedAt"] == item["timestamp"] and "grantedBy" not in item


def test_provisional_Q13_fields_right_after_user(be):
    be.put_state(rules_seed())
    be.ask(FORM, body=FORM_ANSWERS)
    item = only(be, FORM, REQUESTER)[1]
    assert list(item) == ["user", "fields", "timestamp", "status"]


def test_provisional_Q15_only_card_labels_and_json_text(be):
    be.put_state(rules_seed())
    body = {"Company": 42, "I agree to share my contact information": True, "Not a card label": "dropped"}
    assert be.ask(FORM, body=body).status_code == 303
    fields = only(be, FORM, REQUESTER)[1]["fields"]
    assert fields == {"Company": "42", "I agree to share my contact information": "true"}


def test_provisional_Q16_no_field_is_required(be):
    be.put_state(rules_seed())
    assert be.ask(FORM, body={}).status_code == 303
    assert only(be, FORM, REQUESTER)[0] == "pending"


def test_provisional_Q14_report_reviewedAt_last_and_no_email_when_granted(be):
    be.put_state(rules_seed([reviewed(REQUESTER, "rejected")]))
    E.assert_ok(be.grant(MANUAL, {"user": CAROL}))
    entries = {e["user"]: e for e in be.report(MANUAL).json()}
    assert list(entries[REQUESTER])[-1] == "reviewedAt"
    assert "email" not in entries[CAROL] and list(entries[CAROL])[-1] == "reviewedAt"


@pytest.mark.parametrize("q,expected", [
    ("BOri", {REQUESTER}),  # substring of the username, any case
    ("ridg", {REQUESTER}),  # substring of the fullname "Bridge"
    ("example.org", {CAROL}),  # carol's shared e-mail
])
def test_provisional_Q21_q_is_substring_on_username_fullname_shared_email(be, q, expected):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z"), pending(CAROL, "2026-10-05T14:01:00.000Z")]))
    assert {i["user"]["user"] for i in be.list_requests(MANUAL, "pending", f"?q={q}").json()} == expected


def test_provisional_Q21_unshared_email_is_not_searched(be):
    be.put_state(rules_seed())
    E.assert_ok(be.grant(MANUAL, {"user": CAROL}))  # granted: e-mail not shared (REQ-5)
    assert be.list_requests(MANUAL, "accepted", "?q=example.org").json() == []
    assert [i["user"]["user"] for i in be.list_requests(MANUAL, "accepted", "?q=carol").json()] == [CAROL]


def test_provisional_Q24_owner_may_ask_access_on_own_repo(be):
    be.put_state(rules_seed())
    assert be.ask(MANUAL, persona="owner").status_code == 303
    assert only(be, MANUAL, OWNER)[0] == "pending"


@pytest.mark.parametrize("q,expected", [("Test", [REQUESTER]), ("Bri", [REQUESTER]), ("conf-user", ["conf-user-01",
                                        "conf-user-02"]), ("Orig", [])])
def test_provisional_Q25_quicksearch_users_prefix(be, q, expected):
    be.put_state(rules_seed(users=2))
    response = be.get("owner", f"/api/quicksearch?q={q}&type=user")
    E.assert_ok(response)
    users = response.json()["users"]
    assert [u["user"] for u in users] == expected
    assert all(list(u) == ["_id", "avatarUrl", "fullname", "user"] for u in users)


def test_provisional_Q25_quicksearch_other_type_is_400(be):
    be.put_state(rules_seed())
    assert be.get("owner", "/api/quicksearch?q=Test&type=model").status_code == 400


# --- the "(none)" row -----------------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("GET", "/Orosius/does-not-exist-xyz/resolve/main/config.json"),
    ("GET", "/api/models/Orosius/does-not-exist-xyz/auth-check"),
    ("POST", "/Orosius/does-not-exist-xyz/ask-access"),
])
def test_provisional_unknown_repo_logged_in_is_404(be, method, path):
    be.put_state(rules_seed())
    response = be.req("requester", method, path, {} if method == "POST" else None)
    assert response.status_code == 404, E.describe(response)
    assert response.headers.get("x-error-code") == "RepoNotFound"


def test_provisional_private_repo_looks_missing_to_non_owners(be):
    document = rules_seed()
    document["repos"].append(demo_repo("Orosius/conf-private", "manual", ("README.md", "config.json"),
                                       _id="64b0c0ffee0000000000d005"))
    document["repos"][-1]["private"] = True
    be.put_state(document)
    response = be.auth_check("Orosius/conf-private", "requester")
    assert (response.status_code, response.headers.get("x-error-code")) == (404, "RepoNotFound"), E.describe(response)
    E.assert_ok(be.auth_check("Orosius/conf-private", "owner"))


def test_provisional_revisions_and_tree_paths(be):
    be.put_state(rules_seed())
    sha = next(r for r in rules_seed()["repos"] if r["id"] == MANUAL)["sha"]
    E.assert_ok(be.resolve(MANUAL, "config.json", "owner", rev=sha))  # revisions: main and the head sha
    E.assert_error(be.resolve(MANUAL, "config.json", "owner", rev="nonexistent-branch"), 404, "Revision not found",
                   code="RevisionNotFound", body="any")
    response = be.get("anonymous", f"/api/models/{MANUAL}/tree/main/no-such-dir")
    assert (response.status_code, response.headers.get("x-error-code")) == (404, "EntryNotFound"), E.describe(response)


def test_provisional_lfs_redirects_to_resolve_cache_which_applies_the_gate(be):
    from conformance.seeds import LFS_FILE, SANDBOX, scenario_seed
    be.put_state(scenario_seed("clone-seed-reads"))
    response = be.resolve(SANDBOX, LFS_FILE, "owner", method="HEAD")
    assert response.status_code == 302, E.describe(response)
    assert response.headers["location"].startswith(f"{be.base_url}/api/resolve-cache/models/{SANDBOX}/") or \
        response.headers["location"].startswith(f"/api/resolve-cache/models/{SANDBOX}/"), response.headers["location"]
    assert "x-linked-size" in response.headers and "x-linked-etag" in response.headers
    assert "link" not in response.headers  # no xet Link
    location = response.headers["location"].removeprefix(be.base_url)
    gated = be.req("anonymous", "GET", location)
    assert (gated.status_code, gated.headers.get("x-error-code")) == (401, "GatedRepo"), E.describe(gated)


def test_provisional_no_etag_on_307_and_unknown_expand_skipped(be):
    be.put_state(rules_seed())
    redirect = be.resolve(PUBLIC, "config.json", "anonymous")
    assert redirect.status_code == 307 and "etag" not in redirect.headers, E.describe(redirect)
    info = be.get("anonymous", f"/api/models/{MANUAL}?expand[]=gated&expand[]=bogusField")
    assert list(info.json()) == ["_id", "id", "gated"], info.text


def test_provisional_settings_echo_only_gated_private_visibility(be):
    be.put_state(rules_seed())
    response = be.settings(MANUAL, {"gated": "auto", "gatedNotificationsMode": "real-time",
                                    "gatedNotificationsEmail": "x@conformance.test"})
    E.assert_ok(response)
    assert response.json() == {"gated": "auto"}
