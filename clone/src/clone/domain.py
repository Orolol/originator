"""Pure domain logic of the slice: the access decision and the access-request state machine.

No HTTP and no storage: functions take plain values and return new values (or raise a typed
error). Rule IDs refer to docs/hf-gated/behaviour.md; `Provisional (Q-n)` marks a choice recorded
against docs/hf-gated/open-questions.md because the KB is silent.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

Status = Literal["pending", "accepted", "rejected", "reset"]
# Enum order as HF's validation message lists it (REV-12, api.md §3).
STATUSES: tuple[Status, ...] = ("accepted", "rejected", "pending", "reset")
Gated = Literal[False, "auto", "manual"]

# ACC-5: exact names, repo root only, case-sensitive.
ALLOWLIST = frozenset({"README.md", "LICENSE", "LICENSE.md", "LICENSE.txt"})


@dataclass(frozen=True)
class AccessRequest:
    """At most one per (repo, user) (behaviour.md §1)."""

    repo: str
    user: str
    status: Status
    timestamp: str  # TS-1: time of the submission that created the request
    reviewedAt: str | None = None  # TS-2
    grantedBy: str | None = None  # username of whoever accepted (handle accepted or grant)
    fields: dict[str, str] | None = None  # gate-form answers, only when the card has extra fields
    emailShared: bool = True  # False for entries created by grant (REQ-5)


@dataclass(frozen=True)
class Email:
    """An e-mail HF would send (behaviour.md §7); recorded in the outbox, never sent."""

    kind: Literal["new_request", "request_reset"]
    reason: str | None = None


@dataclass(frozen=True)
class Change:
    """Result of a transition: the new request (None = deleted) and the e-mails it triggers."""

    request: AccessRequest | None
    changed: bool
    emails: tuple[Email, ...] = field(default=())


class RequestNotFound(Exception):
    """404 "No access request found matching your criteria" (REV-1, §5.1 table)."""


class AlreadyHasAccess(Exception):
    """400 "That user already has access to the repo" (REV-7)."""


# --- Access decision (ACC-*) ----------------------------------------------------------------


@dataclass(frozen=True)
class Denied:
    status: int  # 401 (anonymous) or 403 (logged in); always X-Error-Code: GatedRepo
    message: str


def gate_message(repo_id: str, request_status: Status | None, *, anonymous: bool) -> str:
    """Exact gate messages, api.md §3.1 [OBS 2026-10-05]."""
    if anonymous:
        return (f"Access to model {repo_id} is restricted. You must have access to it and be "
                "authenticated to access it. Please log in.")
    if request_status == "pending":
        return f"Your request to access model {repo_id} is awaiting a review from the repo authors."
    if request_status == "rejected":
        # REQ-4: the rejection reason is never part of the message.
        return f"Your request to access model {repo_id} has been rejected by the repo's authors."
    if request_status == "reset":
        return (f"Your request to access model {repo_id} has been reset by the repo's authors. "
                f"Visit https://huggingface.co/{repo_id} to submit a new request.")
    return (f"Access to model {repo_id} is restricted and you are not in the authorized list. "
            f"Visit https://huggingface.co/{repo_id} to ask for access.")


def check_access(
    *, repo_id: str, gated: Gated, owner: str, caller: str | None,
    request_status: Status | None, path: str | None = None,
) -> Denied | None:
    """None if `caller` may read gated content; `path` is given on the resolve route only."""
    if gated is False:
        return None  # ACC-7, CFG-6: a non-gated repo behaves like any public repo
    if path is not None and path in ALLOWLIST:
        return None  # ACC-5 (resolve only; the gate is checked before existence, ACC-6)
    if caller is None:
        return Denied(401, gate_message(repo_id, None, anonymous=True))  # ACC-3
    # ACC-1: the owner of a user-namespace repo bypasses the gate. Org repos are not modelled
    # (no org in the seeds), so only the user-namespace case applies.
    if caller == owner or request_status == "accepted":
        return None
    return Denied(403, gate_message(repo_id, request_status, anonymous=False))  # §2 table


# --- Owner transitions (REV-*) -----------------------------------------------------------------


def _with_status(req: AccessRequest, target: Status, now: str, reviewer: str) -> AccessRequest:
    """Stamp a status change. TS-1: `timestamp` is never touched here."""
    if target == "pending":
        return replace(req, status="pending", reviewedAt=None, grantedBy=None)  # TS-2: removed
    if target == "accepted":
        return replace(req, status="accepted", reviewedAt=now, grantedBy=reviewer)
    # rejected / reset: reviewedAt = review time, no grantedBy (REV-3, §1 table) [OBS]
    return replace(req, status=target, reviewedAt=now, grantedBy=None)


def _reset_emails(target: Status, reset_reason: str | None) -> tuple[Email, ...]:
    # REV-3, §7: a reset e-mails the user, with the optional resetReason.
    return (Email("request_reset", reset_reason),) if target == "reset" else ()


def handle(
    current: AccessRequest | None, target: Status, *, now: str, reviewer: str,
    reset_reason: str | None = None,
) -> Change:
    """`POST …/user-access-request/handle` (§5.1).

    REV-1: no request, or a request already in `target`, is the same 404 [OBS C m2/m4/m6].
    Every other move is allowed. Observed: pending→accepted/rejected, accepted→pending/rejected/
    reset, rejected→accepted/reset; rejected→pending per [CLIENT doc].
    Provisional (Q-5): pending→reset and moves out of `reset` are allowed like the others.
    """
    if current is None or current.status == target:
        raise RequestNotFound
    return Change(_with_status(current, target, now, reviewer), True, _reset_emails(target, reset_reason))


def batch_item(
    current: AccessRequest | None, target: Status, *, now: str, reviewer: str,
    reset_reason: str | None = None,
) -> Change:
    """One item of `POST …/batch` (REV-9): unlike `handle`, same status is ok:true, unchanged."""
    if current is None:
        raise RequestNotFound  # → {"ok": false, "error": "request_not_found"}
    if current.status == target:
        return Change(current, False)
    return Change(_with_status(current, target, now, reviewer), True, _reset_emails(target, reset_reason))


def grant(
    current: AccessRequest | None, *, repo: str, user: str, owner: str, now: str, reviewer: str,
) -> Change:
    """`POST …/grant` (REV-6..REV-8)."""
    if current is not None and current.status == "accepted":
        raise AlreadyHasAccess  # REV-7 [OBS W s6-grant-again]
    if user == owner:
        # Provisional (Q-6, self-grant): the owner already has access (ACC-1), so REV-7 applies.
        raise AlreadyHasAccess
    if current is None:
        # REV-6, REQ-5: accepted without a request; email not shared. TS-1: the entry's
        # `timestamp` is the grant time (CLIENT tests only say it is a datetime).
        return Change(AccessRequest(repo, user, "accepted", now, now, reviewer, None, False), True)
    # REV-8 [OBS W s6]: a pending request is accepted, timestamp and email kept.
    # Provisional (Q-6): rejected and reset requests are accepted the same way.
    return Change(_with_status(current, "accepted", now, reviewer), True)


# --- Requester transitions (§4) -----------------------------------------------------------------


def ask_access(
    current: AccessRequest | None, *, repo: str, user: str, gated: Gated, now: str,
    fields: dict[str, str] | None,
) -> Change:
    """`POST /{repo}/ask-access` (§4 table)."""
    if gated is False:
        # Provisional (Q-2): no gate form on a non-gated repo (CFG-5, ACC-7); a post is a no-op 303.
        return Change(current, False)
    if current is None or current.status == "reset":
        # §4: a new request; after reset it gets a new timestamp and loses reviewedAt [OBS W s5b].
        # Provisional (Q-2): the new submission's answers replace the old `fields`.
        if gated == "manual":
            new = AccessRequest(repo, user, "pending", now, None, None, fields, True)
            return Change(new, True, (Email("new_request"),))  # §7: manual mode e-mails the owner
        # auto → accepted immediately [DOC]. Provisional (Q-10): reviewedAt = the same instant
        # (TS-2: "time of the last accept"), no grantedBy (nobody accepted it).
        return Change(AccessRequest(repo, user, "accepted", now, now, None, fields, True), True)
    # pending: 303, unchanged [OBS]; rejected: 303, silently ignored [OBS C m7].
    # Provisional (Q-2): accepted is unchanged too, and a pending re-submit keeps timestamp/fields.
    return Change(current, False)


def cancel(current: AccessRequest | None) -> Change:
    """`POST …/user-access-request/cancel` by the requester (REQ-7 [OBS 2026-10-06]).

    Only a pending request can be withdrawn, and it is deleted (back to "no request"). Any other
    status, or no request, raises: the caller answers 404 and nothing changes.
    """
    if current is None or current.status != "pending":
        raise RequestNotFound
    return Change(None, True)
