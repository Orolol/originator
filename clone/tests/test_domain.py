"""Domain unit tests: the state machine of behaviour.md §4–§5.1, the access decision (ACC-*),
the timestamp rules (TS-*) and the validation message format (REV-12). No HTTP."""

from __future__ import annotations

import pytest
from clone.domain import AccessRequest, AlreadyHasAccess, Email, RequestNotFound
from clone.zod import Issue, header_safe, prettify

from clone import domain

REPO = "Orosius/deltanet-mla-latent"
T0, NOW = "2026-10-05T14:00:00.000Z", "2026-10-05T15:00:00.000Z"


def req(status, **kw) -> AccessRequest:
    reviewed = {"pending": None}.get(status, "2026-10-05T14:10:00.000Z")
    base = dict(reviewedAt=reviewed, grantedBy="Orosius" if status == "accepted" else None)
    return AccessRequest(REPO, "TestingBOrig", status, T0, **(base | kw))


# behaviour.md §5.1, from \ to. "404" = RequestNotFound (REV-1). Provisional cells (Q-5) are the
# moves into reset from pending and every move out of reset.
HANDLE = {
    None: dict.fromkeys(("pending", "accepted", "rejected", "reset"), "404"),
    "pending": {"pending": "404", "accepted": "ok", "rejected": "ok", "reset": "ok"},
    "accepted": {"pending": "ok", "accepted": "404", "rejected": "ok", "reset": "ok"},
    "rejected": {"pending": "ok", "accepted": "ok", "rejected": "404", "reset": "ok"},
    "reset": {"pending": "ok", "accepted": "ok", "rejected": "ok", "reset": "404"},
}


@pytest.mark.parametrize(("start", "target"), [(s, t) for s, row in HANDLE.items() for t in row])
def test_REV_1_handle_matrix(start, target):
    current = req(start) if start else None
    if HANDLE[start][target] == "404":
        with pytest.raises(RequestNotFound):
            domain.handle(current, target, now=NOW, reviewer="Orosius")
        return
    change = domain.handle(current, target, now=NOW, reviewer="Orosius", reset_reason="why")
    new = change.request
    assert new.status == target and new.timestamp == T0  # TS-1: never changed by a review
    # TS-2: reviewedAt = review time, removed when back to pending; grantedBy only when accepted
    assert new.reviewedAt == (None if target == "pending" else NOW)
    assert new.grantedBy == ("Orosius" if target == "accepted" else None)
    # REV-3, §7: only a reset e-mails the requester, with the reason
    assert change.emails == ((Email("request_reset", "why"),) if target == "reset" else ())


@pytest.mark.parametrize("start", [None, "pending", "accepted", "rejected", "reset"])
def test_REV_9_batch_same_status_is_ok_and_unchanged(start):
    current = req(start) if start else None
    if current is None:
        with pytest.raises(RequestNotFound):
            domain.batch_item(current, "pending", now=NOW, reviewer="Orosius")
        return
    change = domain.batch_item(current, start, now=NOW, reviewer="Orosius")
    assert change.changed is False and change.request == current


@pytest.mark.parametrize(("start", "outcome"), [
    (None, "new"),  # REV-6, REQ-5
    ("pending", "accepted"),  # REV-8 [OBS W s6]
    ("rejected", "accepted"),  # Provisional (Q-6)
    ("reset", "accepted"),  # Provisional (Q-6)
    ("accepted", "400"),  # REV-7 [OBS]
])
def test_REV_6_to_8_grant(start, outcome):
    current = req(start) if start else None
    if outcome == "400":
        with pytest.raises(AlreadyHasAccess):
            domain.grant(current, repo=REPO, user="TestingBOrig", owner="Orosius", now=NOW, reviewer="Orosius")
        return
    new = domain.grant(current, repo=REPO, user="TestingBOrig", owner="Orosius", now=NOW, reviewer="Orosius").request
    assert (new.status, new.reviewedAt, new.grantedBy) == ("accepted", NOW, "Orosius")
    assert new.timestamp == (NOW if start is None else T0)
    assert new.emailShared is (start is not None)  # REQ-5: no email for a grant without request


def test_REV_7_owner_self_grant_already_has_access():
    with pytest.raises(AlreadyHasAccess):  # Provisional (Q-6): ACC-1 gives the owner access
        domain.grant(None, repo=REPO, user="Orosius", owner="Orosius", now=NOW, reviewer="Orosius")


@pytest.mark.parametrize(("start", "gated", "expected"), [
    (None, "manual", "pending"),  # §4 [OBS]
    (None, "auto", "accepted"),  # §4 [DOC]
    ("reset", "manual", "pending"),  # §4 [OBS W s5b]: new request, new timestamp
    ("reset", "auto", "accepted"),  # §4 [DOC-implied]
    ("pending", "manual", "unchanged"),  # [OBS]
    ("rejected", "manual", "unchanged"),  # [OBS C m7]: silently ignored
    ("accepted", "manual", "unchanged"),  # Provisional (Q-2)
    (None, False, "unchanged"),  # Provisional (Q-2)
])
def test_REQ_ask_access_transitions(start, gated, expected):
    current = req(start) if start else None
    change = domain.ask_access(current, repo=REPO, user="TestingBOrig", gated=gated, now=NOW, fields=None)
    if expected == "unchanged":
        assert change.changed is False and change.request == current and change.emails == ()
        return
    new = change.request
    assert new.status == expected and new.timestamp == NOW and new.grantedBy is None
    assert new.reviewedAt == (None if expected == "pending" else NOW)
    # §7: only a new request in manual mode e-mails the owner
    assert change.emails == ((Email("new_request"),) if gated == "manual" else ())


def test_REQ_7_cancel_deletes_a_pending_request_only():
    assert domain.cancel(req("pending")) == domain.Change(None, True)
    for current in (None, req("accepted"), req("rejected"), req("reset")):
        with pytest.raises(RequestNotFound):
            domain.cancel(current)


# api.md §3.1 [OBS 2026-10-05]
ANON = ("Access to model {id} is restricted. You must have access to it and be authenticated to "
        "access it. Please log in.")
NO_REQUEST = ("Access to model {id} is restricted and you are not in the authorized list. "
              "Visit https://huggingface.co/{id} to ask for access.")
PENDING = "Your request to access model {id} is awaiting a review from the repo authors."
REJECTED = "Your request to access model {id} has been rejected by the repo's authors."
RESET = ("Your request to access model {id} has been reset by the repo's authors. "
         "Visit https://huggingface.co/{id} to submit a new request.")


@pytest.mark.parametrize(("gated", "caller", "status", "path", "expected"), [
    (False, None, None, ".gitattributes", None),  # ACC-7
    ("manual", None, None, "README.md", None),  # ACC-5
    ("auto", None, None, "LICENSE.txt", None),  # ACC-5
    ("manual", None, None, None, (401, ANON)),  # ACC-3 (auth-check: no allowlist)
    *[("manual", None, None, p, (401, ANON)) for p in (
        "readme.md", "README.MD", "README.txt", "LICENSE.rst", "license.txt", "LICENCE", "COPYING",
        ".gitattributes", "original/README.md", "original/LICENSE.txt")],  # ACC-5 negatives [OBS]
    ("manual", "Orosius", None, "x.bin", None),  # ACC-1
    ("manual", "TestingBOrig", "accepted", "x.bin", None),
    ("auto", "TestingBOrig", None, "x.bin", (403, NO_REQUEST)),
    ("manual", "TestingBOrig", "pending", None, (403, PENDING)),
    ("auto", "TestingBOrig", "pending", None, (403, PENDING)),  # CFG-6: auto does not accept pending
    ("manual", "TestingBOrig", "rejected", None, (403, REJECTED)),
    ("manual", "TestingBOrig", "reset", None, (403, RESET)),
])
def test_ACC_access_decision(gated, caller, status, path, expected):
    denied = domain.check_access(repo_id=REPO, gated=gated, owner="Orosius", caller=caller,
                                 request_status=status, path=path)
    if expected is None:
        assert denied is None
    else:
        assert (denied.status, denied.message) == (expected[0], expected[1].format(id=REPO))


@pytest.mark.parametrize(("issues", "body", "header"), [
    ([Issue("Too big: expected string to have <=200 characters", ("rejectionReason",))],
     "✖ Too big: expected string to have <=200 characters\n  → at rejectionReason",
     "* Too big: expected string to have <=200 characters * at rejectionReason"),  # [OBS W s7]
    ([Issue("Either userId or user must be provided, but not both")],
     "✖ Either userId or user must be provided, but not both",
     "* Either userId or user must be provided, but not both"),  # [OBS W s7]
    # Provisional (Q-9): several issues, sorted by path depth; array indexes in brackets
    ([Issue("b", ("requests", 0, "userId")), Issue("a", ("status",))],
     "✖ a\n  → at status\n✖ b\n  → at requests[0].userId", "* a * at status * b * at requests[0].userId"),
])
def test_REV_12_validation_message_format(issues, body, header):
    assert prettify(issues) == body
    assert header_safe(body) == header
