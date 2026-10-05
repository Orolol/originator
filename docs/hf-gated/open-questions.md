# Open questions (unverified behaviour)

Every behaviour the sources do not pin down. **Rule**: the clone may implement a provisional answer
only if this file records the choice (`Provisional:`). When a question is resolved, write the
answer, the evidence (`[OBS]` + date + fixture path) and the rules it updates. Do not delete entries.

Priority: **P0** blocks the core state machine or the bridge; **P1** UI fidelity; **P2** edge or later.

How to resolve: almost all of these need two real accounts, **owner** and **requester**, and a
**throwaway sandbox repo** owned by the owner account. Use the bridge or a recorded manual session
([ui.md](ui.md) §E), never someone else's repo.

---

### Q-1 (P0): can the requester side be driven by API?
`POST /{ns}/{repo}/ask-access`: does it accept `Authorization: Bearer` (the docs say "only from your
browser"), or does it need the web session cookie (and a CSRF token)? Form-encoded or JSON? What does
a non-browser client get back (303 + `Location`)? **Decides the bridge design for the requester
screens.**
**Answer (2026-10-05) [OBS]**: yes. With a write-role user token, JSON `{}` and form `{}` both give
`303 Location: https://huggingface.co/{id}`, and the request lands in `pending` (manual repo, no
extra fields). No CSRF token or cookie is needed. HTML pages ignore Bearer tokens
(`isLoggedIn: false`), so screens still need a browser login. Evidence:
`observations/2026-10-05-requester-ask-access.{md,json}`. Updates REQ-2 and api.md §1.
Remaining: a read-role token, a fine-grained token, an anonymous post. Status: **mostly resolved**.

### Q-2 (P0): re-submitting `ask-access` when a request exists
Responses for a `pending`, `accepted`, `rejected` ("cannot request again": what status and message?)
and `reset` requester. On re-request after reset: is `timestamp` new, and are the `fields` replaced?
Partial (2026-10-05) [OBS]: re-submitting while `pending` → `303` to the repo, no error, still
pending. Whether that touches `timestamp` needs the owner's list view. Status: open for
accepted, rejected and reset.

### Q-3 (P0): requester self-cancel
`POST /api/models/{id}/user-access-request/cancel`: is the request deleted (back to "no request") or
moved to a status? From which states is it allowed? What is the error when there is no request? Is
there a UI control for it? Status: open.

### Q-4 (P0): same-status and success responses
Exact status code and body for handle → the current status (the docstrings say 404 "already in the …
list"); the success body of `handle`; how `batch` reports an item already in the target status (`ok:
true`? `request_not_found`?). Status: open.

### Q-5 (P0): `reset` transitions
From which states (pending? rejected? accepted?) is `reset` allowed? Does the request stay listed under
`/reset` until the user re-requests? Can the owner move a `reset` request to accepted, rejected or
pending directly? Status: open.

### Q-6 (P0): grant edge cases
`grant` for a user who is `pending`, `rejected` or `reset`: moves to accepted, or 400? The grant
response body (the client returns `response.json()`)? The `timestamp` and `grantedBy` of a granted
entry? Can the owner grant themselves? Status: open.

### Q-7 (P0): approval-mode changes
manual→auto while requests are pending: auto-accepted, or left pending? auto→manual: no effect?
gated→false: are requests kept? false→gated again: do accepted users keep access, and do lists
reappear? Status: open.

### Q-8 (P0): content-route errors for a logged-in requester, per status
For `resolve` and `auth-check`, with the requester's token, in each state (no request, pending,
rejected, reset, accepted): status code, `X-Error-Code`, `X-Error-Message`.
Resolved (2026-10-05) [OBS]: no request → `403 GatedRepo` "…not in the authorized list. Visit … to
ask for access."; pending → `403 GatedRepo` "Your request to access model {id} is awaiting a
review from the repo authors." Both are identical on `auth-check`, `resolve` GET and HEAD. Status: open
for rejected, reset and accepted.

### Q-9 (P1): owner-side error bodies and validation
Bodies and `X-Error-Message` for: repo not gated (400), unknown user (404), no request (404),
read-only token (403), `rejectionReason` > 200 characters, `rejectionReason` with a non-rejected status
(rejected, ignored or stored?), invalid `status`, `limit` < 10, both `user` and `userId` (or neither).
Partial (2026-10-05) [OBS]: a non-owner calling the list endpoint → `403`, no `X-Error-Code`,
"You have read access but not the required permissions for this operation". Status: open.

### Q-10 (P1): list ordering and timestamps
Default order of each list (by `timestamp`? `reviewedAt`? ascending or descending?). Which field
`after`/`before` filter on. Is `reviewedAt` cleared on cancel → pending? Is `grantedBy` `{}` for
self-service accepts and auto-approvals? Status: open.

### Q-11 (P1): logged-in gate screens
Exact texts and controls for A2–A6 in [ui.md](ui.md): the default button label in auto vs manual; field
order (YAML order?); the post-submit message; the rejected screen with its reason; whether the reset
screen shows `resetReason`; the logged-in `RepoGatedModal` props (status, reason, email…). Status: open.

### Q-12 (P1): settings section mechanics
Does each control save immediately? Are there confirmation dialogs (disable)? The default
`gatedNotificationsMode` and the label of the real-time option; email validation feedback; the view
for org members with a read role. Status: open.

### Q-13 (P1): review modal details
What `Review access requests (N)` counts; whether a `reset` tab exists; how `fields` answers are
displayed; the rejection-reason input; actions on the rejected tab; search, pagination, bulk
selection; refresh behaviour after an action. Status: open.

### Q-14 (P1): access report format
JSON (as the docs say) or CSV? Filename (`Content-Disposition`)? Does it include `fields` and `reset`
entries? Ordering? Status: open.

### Q-15 (P1): stored answer encoding
How answers are stored in `fields`: checkbox (`"on"`? `"true"`?), select (value or label?), date
format, country (code or name), and the value of `ip_location`. Status: open.

### Q-16 (P1): form validation
Are all extra fields required? Must checkboxes be checked? Is it enforced client-side, server-side,
or both? Error messages? Status: open.

### Q-17 (P2): bypass rules in detail
On user-owned repos, does anyone besides the owner bypass (for example, HF staff)? With org repos and
`orgMembersGated=false`, do read-role members bypass? [DOC-implied: yes] Status: open.

### Q-18 (P2): email in lists
Is `user.email` always present for self-service requests? Is it ever hidden (user privacy settings)?
Status: open.

### Q-19 (P2): rejection reason visibility
The owner cannot read `rejectionReason` back through the list API (it is not in the schema). Is it
in the report? How does the requester page render it? Status: open.

### Q-20 (P2): notification side effects
Can an owner observe the "new request" email or the reset email in a test mailbox, with what content
and when (bulk = daily)? The clone only records an outbox. Status: open; likely stays a documented gap.

### Q-21 (P2): search semantics
How `q` matches (substring or prefix? case-insensitive?), what "email domain" and "verified
organization" matching mean, and how combining `q` with pagination behaves. Status: open.

### Q-22 (P2): `gated: true` in README YAML
The EU section of the docs shows `gated: true` in card metadata. Does YAML `gated` do anything, or is
gating only set through settings? Status: open.

### Q-23 (P2): eventual consistency on the real Hub
The client tests sleep 1 s after writes. How long until the lists, `auth-check` and `resolve` reflect a
change? This affects the bridge-vs-clone diff tolerance. Status: open.

### Q-24 (P2): self and deleted users
Can a repo owner `ask-access` on their own repo, or appear in the lists? In the list schema `user` is
not required: what does an entry for a deleted account look like? Status: open.
