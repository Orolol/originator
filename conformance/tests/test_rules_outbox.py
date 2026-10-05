"""E-mail side effects recorded in the outbox (behaviour.md §7, system.md "Outbox entry").

Only the effects §7 documents are asserted here: a new request in manual mode notifies the
notification recipient (gatedNotificationsEmail, else the owner), and a reset e-mails the user with
the reason. What is NOT e-mailed is mostly unknown (Q-20); those checks live in
test_provisional_clone.py.
"""

from __future__ import annotations

from conformance import expect as E
from conformance.rule_seeds import AUTO, AUTO_FIELDS, MANUAL, REQUESTER, rules_seed
from conformance.seeds import OWNER_EMAIL, REQUESTER_EMAIL, request

ENTRY_KEYS = {"id", "at", "to", "kind", "repo", "user"}


def test_new_request_in_manual_mode_notifies_owner(be):
    be.put_state(rules_seed())
    assert be.outbox() == []  # PUT state clears the outbox (system.md)
    assert be.ask(MANUAL).status_code == 303
    outbox = be.outbox()
    assert len(outbox) == 1, outbox
    entry = outbox[0]
    assert ENTRY_KEYS <= set(entry), entry
    assert (entry["kind"], entry["to"], entry["repo"], entry["user"]) == ("new_request", OWNER_EMAIL, MANUAL, REQUESTER)


def test_new_request_goes_to_notification_email_when_set(be):
    be.put_state(rules_seed())
    E.assert_ok(be.settings(MANUAL, {"gatedNotificationsEmail": "gate-review@conformance.test"}))
    assert be.ask(MANUAL).status_code == 303
    entries = [e for e in be.outbox() if e["kind"] == "new_request"]
    assert [e["to"] for e in entries] == ["gate-review@conformance.test"], entries


def test_no_new_request_mail_in_auto_mode(be):
    # system.md: new_request is manual mode only (§7 documents the manual-mode notification)
    be.put_state(rules_seed())
    assert be.ask(AUTO, body={label: "on" for label in AUTO_FIELDS}).status_code == 303
    assert [e for e in be.outbox() if e["kind"] == "new_request"] == []


def test_reset_mails_the_user_with_reason(be):
    be.put_state(rules_seed([request(REQUESTER, "accepted", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                                     "Orosius", repo=MANUAL)]))
    E.assert_ok(be.handle(MANUAL, {"user": REQUESTER, "status": "reset", "resetReason": "Please agree again."}))
    entries = [e for e in be.outbox() if e["kind"] == "request_reset"]
    assert len(entries) == 1, be.outbox()
    entry = entries[0]
    assert (entry["to"], entry["repo"], entry["user"], entry.get("reason")) == (
        REQUESTER_EMAIL, MANUAL, REQUESTER, "Please agree again.")


def test_reset_through_batch_mails_each_user(be):
    be.put_state(rules_seed([request(REQUESTER, "rejected", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                                     repo=MANUAL)]))
    E.assert_ok(be.batch(MANUAL, {"status": "reset", "resetReason": "Batch reset.", "requests": [{"user": REQUESTER}]}))
    entries = [e for e in be.outbox() if e["kind"] == "request_reset"]
    assert [(e["to"], e.get("reason")) for e in entries] == [(REQUESTER_EMAIL, "Batch reset.")], be.outbox()


def test_resubmit_after_reset_is_a_new_request(be):
    # behaviour.md §4: after reset, submitting creates a new request -> manual-mode notification again
    be.put_state(rules_seed([request(REQUESTER, "reset", "2026-10-05T14:00:00.000Z", "2026-10-05T14:05:00.000Z",
                                     repo=MANUAL)]))
    assert be.ask(MANUAL).status_code == 303
    assert [e["kind"] for e in be.outbox()] == ["new_request"]


def test_outbox_delete_clears(be):
    be.put_state(rules_seed())
    be.ask(MANUAL)
    assert be.outbox()
    assert be.clear_outbox().status_code < 300
    assert be.outbox() == []
