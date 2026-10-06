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
pending. Whether that touches `timestamp` needs the owner's list view. Answer (2026-10-05) [OBS, `observations/2026-10-05-owner-walkthrough.md` s5b, `observations/2026-10-05-owner-walkthrough-completion.md` m7]:
- after **rejected** → `303`, silently ignored (still rejected);
- after **reset** → a new `pending` request with a new `timestamp` and no `reviewedAt`.
Status: open for `accepted` and for `timestamp` on a re-submit while pending.

### Q-3 (P0): requester self-cancel
`POST /api/models/{id}/user-access-request/cancel`: is the request deleted (back to "no request") or
moved to a status? From which states is it allowed? What is the error when there is no request? Is
there a UI control for it? Weak evidence (2026-10-05): the account owner cancelled a pending request by hand on huggingface.co
(the exact UI action is not recorded). Afterwards the request was gone from every list and the
requester's `auth-check` said "not in the authorized list". That fits a deletion, which is the clone's
provisional choice, if the action was the requester-side cancel. The web UI now offers a
provisional self-cancel button on A3 (web choice #26). Status: open.

### Q-4 (P0): same-status and success responses
Exact status code and body for handle → the current status (the docstrings say 404 "already in the …
list"); the success body of `handle`; how `batch` reports an item already in the target status (`ok:
true`? `request_not_found`?). **Answer (2026-10-05) [OBS, `observations/2026-10-05-owner-walkthrough-completion.md` m2/m4/m6]**:
- handle → current status gives `404`, JSON `{"error": "No access request found matching your
  criteria"}`, with the same `X-Error-Message` and no `X-Error-Code`, identical to "no request";
- handle success → `200 {}`;
- in `batch`, an item already in the target status → `{"user", "ok": true}`.
Updates REV-1 and REV-9. Status: **resolved**.

### Q-5 (P0): `reset` transitions
From which states (pending? rejected? accepted?) is `reset` allowed? Does the request stay listed under
`/reset` until the user re-requests? Can the owner move a `reset` request to accepted, rejected or
pending directly? Partial (2026-10-05) [OBS]:
- reset is allowed from `accepted` (`observations/2026-10-05-owner-walkthrough.md` s5) and from `rejected` (`observations/2026-10-05-owner-walkthrough-completion.md` m8);
- the entry stays in the `reset` list (`reviewedAt` = reset time) until the user re-requests, which
  creates a new pending request.
Status: open for reset from `pending` and for owner transitions out of `reset`.

### Q-6 (P0): grant edge cases
`grant` for a user who is `pending`, `rejected` or `reset`: moves to accepted, or 400? The grant
response body (the client returns `response.json()`)? The `timestamp` and `grantedBy` of a granted
entry? Can the owner grant themselves? Partial (2026-10-05) [OBS, `observations/2026-10-05-owner-walkthrough.md` s6]:
- grant on a **pending** user → `200 {}`, accepted with `reviewedAt` = grant time, `grantedBy` =
  owner, and its `timestamp` kept;
- grant again → `400 That user already has access to the repo`.
Status: open for rejected and reset users, and for self-grant.

### Q-7 (P0): approval-mode changes
manual→auto while requests are pending: auto-accepted, or left pending? auto→manual: no effect?
gated→false: are requests kept? false→gated again: do accepted users keep access, and do lists
reappear? **Answer (2026-10-05) [OBS, `observations/2026-10-05-owner-walkthrough.md` s9–s10 + UI walkthrough]**:
- manual→auto leaves pending requests pending;
- gated→false keeps all requests, the owner lists still answer 200, and files are public;
- false→manual or auto restores the same lists.
See CFG-6. Status: **resolved** (auto→manual with requests not exercised, but nothing suggests an effect).

### Q-8 (P0): content-route errors for a logged-in requester, per status
For `resolve` and `auth-check`, with the requester's token, in each state (no request, pending,
rejected, reset, accepted): status code, `X-Error-Code`, `X-Error-Message`.
Resolved (2026-10-05) [OBS]: no request → `403 GatedRepo` "…not in the authorized list. Visit … to
ask for access."; pending → `403 GatedRepo` "Your request to access model {id} is awaiting a
review from the repo authors." Both are identical on `auth-check`, `resolve` GET and HEAD. Update (2026-10-05) [OBS, `observations/2026-10-05-owner-walkthrough-completion.md` m1/m5/m8]:
- accepted → `200` (`OK`);
- rejected → `403 GatedRepo` "Your request to access model {id} has been rejected by the repo's
  authors." (no reason);
- reset → `403 GatedRepo` "Your request to access model {id} has been reset by the repo's authors.
  Visit https://huggingface.co/{id} to submit a new request."
Status: **resolved**. The rest of this entry predates the update:
for rejected, reset and accepted.

### Q-9 (P1): owner-side error bodies and validation
Bodies and `X-Error-Message` for: repo not gated (400), unknown user (404), no request (404),
read-only token (403), `rejectionReason` > 200 characters, `rejectionReason` with a non-rejected status
(rejected, ignored or stored?), invalid `status`, `limit` < 10, both `user` and `userId` (or neither).
Partial (2026-10-05) [OBS]: a non-owner calling the list endpoint → `403`, no `X-Error-Code`,
"You have read access but not the required permissions for this operation". Update (2026-10-05) [OBS, `observations/2026-10-05-owner-walkthrough.md` s7]: the observed responses are
- unknown user → `404 User not found`;
- invalid status → `400 * Invalid option: expected one of "accepted"|"rejected"|"pending"|"reset" * at status`;
- reason > 200 → `400 * Too big: expected string to have <=200 characters * at rejectionReason`;
- neither `user` nor `userId` → `400 * Either userId or user must be provided, but not both`;
- `limit=5` → `400 * Too small: expected number to be >=10 * at limit`.
None of them carries an `X-Error-Code`. Status: open for read-only tokens, `rejectionReason` sent
with a non-rejected status, and a non-gated repo with no requests.

### Q-10 (P1): list ordering and timestamps
Default order of each list (by `timestamp`? `reviewedAt`? ascending or descending?). Which field
`after`/`before` filter on. Is `reviewedAt` cleared on cancel → pending? Is `grantedBy` `{}` for
self-service accepts and auto-approvals? Partial (2026-10-05) [OBS]:
- `reviewedAt` is set by accept, reject, reset and grant, and removed when the request goes back to
  pending;
- `grantedBy` is the accepting user (owner) for both handle-accepted and grant, and absent otherwise;
- `timestamp` never changes except on a re-request after reset (TS-1, TS-2).
Status: open for ordering and the `after`/`before` field.

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
entries? Ordering?
Partial (2026-10-05) [OBS]: JSON, `attachment; filename=user-access-report-{ns}-{name}.json`;
pending entry keys `fullname, user, email, time, status`. Status: open for `fields`,
`reviewedAt` on reviewed entries, `reset` entries, and ordering.

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
in the report? How does the requester page render it? Partial (2026-10-05) [OBS]: the reason is absent from the lists, from the report entry, and from
the requester's `auth-check`/`resolve` messages. Status: open for the page rendering and the email.

### Q-20 (P2): notification side effects
Can an owner observe the "new request" email or the reset email in a test mailbox, with what content
and when (bulk = daily)? The clone only records an outbox. Status: open; likely stays a documented gap.

### Q-21 (P2): search semantics
How `q` matches (substring or prefix? case-insensitive?), what "email domain" and "verified
organization" matching mean, and how combining `q` with pagination behaves. Partial (2026-10-05) [OBS]: `q=testingb` matched `TestingBOrig`, so matching is case-insensitive
and a prefix is enough. Status: open.

### Q-22 (P2): `gated: true` in README YAML
The EU section of the docs shows `gated: true` in card metadata. Does YAML `gated` do anything, or is
gating only set through settings? Status: open.

### Q-23 (P2): eventual consistency on the real Hub
The client tests sleep 1 s after writes. How long until the lists, `auth-check` and `resolve` reflect a
change? This affects the bridge-vs-clone diff tolerance. Status: open.

### Q-24 (P2): self and deleted users
Can a repo owner `ask-access` on their own repo, or appear in the lists? In the list schema `user` is
not required: what does an entry for a deleted account look like? Status: open.

### Q-27 (P2): `/raw/` and `/blob/` details
ACC-10 records the gate on `/raw/` (anonymous 401, pending 403, owner 200 text), and an anonymous
`/blob/` 401 is HTML with `X-Error-Code: GatedRepo` and **no** `WWW-Authenticate` [OBS]. Unrecorded:
- `/raw/` on an LFS file (pointer or content?);
- `/raw/` on a non-gated repo (200 or a 307 like resolve?);
- the `/blob/` page content with access, and its 404s;
- HEAD on `raw`/`blob`.
Status: open.

### Q-25 (P1): user search for "Add access"
`GET /api/quicksearch?q=<username>&type=user` returns `users: []` for token callers (owner token,
queries `Orosius`, `TestingBOrig`, `julien-c`); models are returned, and `type=users` is a validation
error. [OBS 2026-10-05, UI builder via bridge] Which endpoint does HF's "Add access" search use,
and does it need a browser session? Until then, "Add access" cannot find anyone in bridge mode, though
`grant` itself works by username through the API. Status: open.

---

## Provisional choices in the web UI (2026-10-05)

Recorded from the UI builder's report (`harness/agents/runs/2026-10-05-ui-builder.md`). Each one is
marked `Provisional (Q-n)` in `web/src`. Resolve them by recording the real UI, then update the code
and strike the line.

| # | Q | Choice |
|---|---|---|
| 1 | Q-11 | Pending (A3): show the backend's auth-check message verbatim (`role=status`) instead of the form. |
| 2 | Q-11 | Accepted (A4) and owner both get 200 from auth-check: no gate box, no banner. |
| 3 | Q-11 | Default submit label is the same in auto and manual mode. |
| 4 | Q-11 | The gate form's `Cancel` does nothing. |
| 5 | Q-16 | No client-side validation (no `required`); selects and the country dropdown start with an empty option. |
| 6 | Q-15 | Native browser values: checkbox `"on"` only when checked; date `YYYY-MM-DD`; country = alpha-2 code; select = option `value`. |
| 7 | Q-15 | `ip_location` renders no input; an unknown field type renders as a text input. |
| 8 | (none) | `Log in` / `Sign Up` link to the persona switch (`/-/persona?as=requester`), since there is no login page. |
| 9 | Q-12 | Each settings control saves immediately (one PUT); no confirmation on Disable; a failed PUT keeps the old value and shows the error. |
| 10 | Q-12 | Notification fields start at `Once a day` (`bulk`) and an empty email (they are unreadable, CFG-3), then show the last PUT echo. Real-time label "Real-time". Email saved on Enter or blur, `type=text`, no validation. |
| 11 | Q-12 | Non-owner on settings: a 401/403 from the pending list is shown verbatim instead of the section. |
| 12 | Q-12 | The "Settings" link on the model page is shown when the whoami name or one of its orgs equals the namespace. |
| 13 | Q-12 | "Add access" dialog: a search box labelled "Username"; clicking a result grants immediately, closes the dialog and refreshes the lists. |
| 14 | Q-13 | `Review access requests (N)`: N = pending count; no number while unknown. |
| 15 | Q-13 | Tabs pending / accepted / rejected only (no reset tab); all three lists are fetched when the modal opens. |
| 16 | Q-13 | Rejected-tab actions: `Accept`, `Cancel`. |
| 17 | Q-13 | `Reject` sends `{user, status:"rejected"}` without a reason input. |
| 18 | Q-13 | Form answers shown as a label → value list under the row. |
| 19 | Q-13 | The × close button is labelled "Close"; no Escape or backdrop close; no avatars; the username links to `/{user}` (404 in our app). |
| 20 | Q-23 / Q-13 | After a handle or grant, all lists are refetched after 1000 ms; no optimistic update; buttons are not disabled in flight. |
| 21 | Q-9 / Q-12 | Errors render as `<p role="alert">{status} {code}: {message}</p>`. |
| 22 | (none) | Unmapped gate states: the message is shown verbatim, plus `[unmapped gate state: auth-check HTTP {status} {code}]`. |
| 24 | Q-11 / Q-19 | Rejected (A5): show the docs' page text `Your request to access this repo has been rejected by the repo's authors.`; no reason (not exposed by the API). |
| 25 | Q-11 | Reset (A6): show the consent form again, with no reset notice. |
| 26 | Q-3 | Pending (A3): a `Cancel my request` button (label invented) posts the web-only route `/-/cancel-request`, which calls `POST …/user-access-request/cancel` with no body and redirects to the repo page; a backend error is shown verbatim. Offered on A3 only (accepted users see no gate box; rejected/reset untested). Added 2026-10-06. |
| 23 | (none) | Settings control order follows the doc screenshots: `New requests` select, `Review access requests (N)`, `Download user access report`, `Add access` on one row; notifications on the next row. The Disable/Enable button sits under the text, not at the top right. |

## Provisional choices in the clone (2026-10-05)

Recorded from the clone builder's report (`harness/agents/runs/2026-10-05-clone-builder.md`), marked
`Provisional (Q-n)` in `clone/src`. When one is recorded on the real Hub, update the clone, its
tests, and this table.

| Q | Choice |
|---|---|
| Q-1 / REQ-1 | Anonymous `ask-access` → 401 `Invalid username or password.` with an HTML body. |
| Q-2 | Re-submit while accepted → no-op; re-submit while pending keeps `timestamp` and `fields`; `ask-access` on a non-gated repo → no-op 303; after reset, the new submission's `fields` replace the old ones. |
| Q-3 | Requester self-cancel deletes the caller's request whatever its status, answering `{}`; with no request → the handle 404. |
| Q-5 | pending→reset and every move out of `reset` are allowed (uniform rule: any change is OK, same status → 404). |
| Q-6 | Granting a rejected or reset user accepts them like a pending one; self-grant → 400 "already has access" (ACC-1). |
| Q-9 | No "repo not gated" 400 on grant/handle (wording unknown, and CFG-6 shows the lists still work). Check order: validation → unknown user → request lookup. A reason sent with another status is ignored. Unrecorded zod wordings are guessed (`gated`, email, datetime, batch item refinement). An empty body is treated as `{}`. |
| Q-10 | Lists sorted by `timestamp` ascending, then insertion order. `after`/`before` filter on `timestamp` (exclusive). The `Link` next URL uses `after` = the last timestamp of the page. An auto-accept sets `reviewedAt` = `timestamp`, with no `grantedBy`. |
| Q-13 / Q-15 / Q-16 | `fields` sits right after `user` in list items. Only the card's labels are stored. Non-string JSON values are stored as JSON text. No field is required. |
| Q-14 | The report is one sequence of every request, all statuses mixed, sorted like the lists (Q-10: `timestamp` ascending, then insertion order). It adds `reviewedAt` as the last key when set and has no `email` for granted users. |
| Q-21 | `q` = case-insensitive substring on username, fullname and the shared email. |
| Q-24 | An owner may `ask-access` on their own repo like anyone. |
| Q-25 | quicksearch → `{"users": [{_id, avatarUrl, fullname, user}]}`, username or fullname prefix, seed order. `type` other than `user` → 400. |
| Q-27 | `/raw/` on an LFS file serves the git blob, i.e. the pointer (ETag = git oid). `/raw/` on a non-gated repo → 200 directly, without the 307. The `/blob/` page with access shows the escaped content (the pointer for LFS, only the size above 1 MiB); blob 404s are HTML; a blob 401 for an unknown repo keeps `WWW-Authenticate`. raw and blob answer GET only. |
| (none) | ACC-9 masking implemented per the recording; "access" = the auth-check decision (the allowlist does not count). A logged-in caller on an unknown repo → 404 RepoNotFound on resolve, auth-check and ask-access. A private repo looks missing to non-owners. `RevisionNotFound` "Revision not found" (revisions: `main`, head sha). Unknown tree path → 404 EntryNotFound. LFS → 302 to the clone's `/api/resolve-cache/…` with `X-Linked-Size`/`X-Linked-Etag`, and no xet `Link`. `resolve-cache` applies the gate. No ETag on a 307. Unknown `expand[]` names are skipped. The settings echo returns only `gated`/`private`/`visibility`. |
