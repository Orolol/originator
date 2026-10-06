# Behaviour spec: gated models (access-request lifecycle)

The core business logic the clone must reproduce. Every rule has an ID (cite it in tests,
commits and divergence notes) and evidence tags (legend in [../README.md](../README.md)).
Rules marked `[Q-n]` depend on an open question in [open-questions.md](open-questions.md):
**do not implement a guess for them without recording it as a provisional choice.**

HTTP details are in [api.md](api.md), screens in [ui.md](ui.md), the gate form in
[gate-form.md](gate-form.md).

## 1. Entities

### Repo gating configuration

| Field | Values | Default | Evidence |
|---|---|---|---|
| `gated` | `false` \| `"auto"` \| `"manual"` | `false` (new repos are not gated) | [DOC] [SPEC] [CLIENT] |
| `orgMembersGated` | bool, org-owned repos only | `false` | [DOC] [SPEC] |
| `gatedNotificationsMode` | `"bulk"` (UI: "Once a day") \| `"real-time"` | UI screenshot shows "Once a day" [DOC]; API default unknown [Q-12] | [DOC] [SPEC] |
| `gatedNotificationsEmail` | email or unset | unset → owner's primary email; org repo → first 5 org admins | [DOC] [SPEC] |
| Card metadata `extra_gated_*` | see gate-form.md | absent | [DOC] |

- **CFG-1** Enabling access requests from the UI starts in **automatic approval**. [DOC]
- **CFG-2** `gated` is set with `PUT /api/models/{id}/settings`. The server schema accepts only
  `false`, `"auto"`, `"manual"`, and `true` is not valid. [SPEC] The Python client raises `ValueError`
  for anything else before sending. [CLIENT]
- **CFG-3** The settings response echoes **only the fields sent**. `PUT {}` → `200 {}`, so an
  empty payload is accepted server-side, whereas the Python client refuses it. There is no
  `GET …/settings` (404), and model info does not expose the notification settings, so they are
  write-only through the API. [OBS 2026-10-05] (The spec only says "the updated repo settings". [SPEC])
- **CFG-4** `gated` and `private` are independent; a repo can be both private and gated. [CLIENT tests]
- **CFG-5** `extra_gated_*` metadata has no effect while `gated == false`. A live repo
  (`mistralai/Mistral-7B-v0.1`) has `extra_gated_description` with `gated: false`. [OBS]
- **CFG-6** Changing the mode keeps every request where it is [OBS 2026-10-05, W s9–s10, UI walkthrough]:
  - **manual → auto** does **not** auto-accept pending requests. The requester still gets
    "awaiting a review" in auto mode.
  - **gated → false**: the requester and anonymous users can download (`auth-check` 200; anonymous
    `resolve` → `307` to `/api/resolve-cache/models/{id}/{sha}/{path}?…`). The owner list endpoint still
    answers `200` with the stored requests, which contradicts the client docstring "400 if the repo
    is not gated", at least when requests exist.
  - **false → manual / auto**: the stored requests reappear unchanged, and the pending requester is
    "awaiting a review" again.

  (W = `observations/2026-10-05-owner-walkthrough.md`.)
- **CFG-7** `PUT …/settings {gatedNotificationsMode}` → `200 {}`: the notification fields are not
  even echoed (unlike `gated`), so the API gives no confirmation that they were stored. [OBS 2026-10-05,
  `observations/2026-10-05-ui-walkthrough.md` #245–246]

### Access request

There is at most one request per (repo, user). Shape as listed by the API [SPEC]:

| Field | Meaning | Evidence |
|---|---|---|
| `user` | requester profile: `user` (username), `fullname`, `_id` (24-hex ObjectId), `avatarUrl`, `isPro`, `type: "user"`, `verifiedOrgNames`, optional `email`, `orgs`, … | [SPEC] |
| `status` | `pending` \| `accepted` \| `rejected` \| `reset` | [SPEC] [DOC] |
| `fields` | answers to the gate form, map `label → string` | [SPEC] [CLIENT] |
| `timestamp` | when the user initially made the request (required) | [SPEC] [DOC] |
| `reviewedAt` | time of the last accept, reject, reset or grant; removed when the request goes back to pending | [SPEC] [DOC] [OBS 2026-10-05] |
| `grantedBy` | user object of whoever **accepted** (`handle` accepted or `grant`), e.g. the owner. It is absent for pending, rejected and reset entries | [SPEC] [OBS 2026-10-05] |

- **REQ-4** `rejectionReason` and `resetReason` are **not** in the list item schema
  (`additionalProperties: false`), and observed lists never contain them. The requester's API error
  message does not include them either. [SPEC] [OBS 2026-10-05] Where the requester sees the reason
  (page or email) is [Q-19].
- **REQ-6** Observed list-item key order: `user, timestamp, reviewedAt, status, grantedBy`, with
  absent keys skipped (a pending item is `user, timestamp, status`). [OBS 2026-10-05]
- **REQ-5** `user.email` is absent/`null` for users added through **grant**. The client test
  says: "email not shared when granted access manually". [CLIENT tests]

## 2. States and what they allow

"No request" is a real state: the user has never interacted, or the request was removed [Q-3].
The content-route answer is the same on `auth-check`, `resolve` GET and HEAD. [OBS 2026-10-05]

| State | Content routes answer (requester token) | Re-submitting the form | Shown on repo page | Evidence |
|---|---|---|---|---|
| no request | `403 GatedRepo` "Access to model {id} is restricted and you are not in the authorized list. Visit https://huggingface.co/{id} to ask for access." | creates the request (§4) | consent form | [DOC] [OBS] |
| `pending` | `403 GatedRepo` "Your request to access model {id} is awaiting a review from the repo authors." | `303`, no change | "awaiting review" message [Q-11] | [DOC] [OBS] |
| `accepted` | `200` (`auth-check` body `OK`; files served) | unknown [Q-2] | no gate box | [DOC] [OBS] |
| `rejected` | `403 GatedRepo` "Your request to access model {id} has been rejected by the repo's authors." (no reason) | `303`, **silently ignored**, stays `rejected` ("cannot request access again") | "Your request to access this repo has been rejected by the repo's authors." + reason if any | [DOC] [OBS] |
| `reset` | `403 GatedRepo` "Your request to access model {id} has been reset by the repo's authors. Visit https://huggingface.co/{id} to submit a new request." | creates a **new** request (§4) | consent form again [DOC]; extra notice [Q-11] | [DOC] [OBS] |

## 3. Who bypasses the gate

- **ACC-1** In a gated repo, a user can read gated content iff one of these holds:
  - they own the repo (user namespace);
  - the repo is org-owned, they are a member, and `orgMembersGated` is false;
  - the repo is org-owned, `orgMembersGated` is true, and they are an org admin, the repo creator,
    or an admin of the repo's Resource Group;
  - their request status is `accepted`.

  Evidence: [DOC]. Members with the read, contributor or write role all bypass by default; that
  part is [DOC-implied].
- **ACC-2** Access is always per individual user, never per organization. [DOC]
- **ACC-3** Anonymous callers can never read gated content, except for the allowlist in ACC-5. [OBS]
- **ACC-4** These stay public on a gated (public) repo, with no access needed: the model page,
  `GET /api/models/{id}` (including `gated` and `cardData`), `…/revision/{rev}`, the tree listing
  (paths, sizes, oids), and the discussions page and API. [OBS]
- **ACC-5** **Allowlist (resolve route only).** `/{id}/resolve/{rev}/{path}` skips the gate when
  `path` is exactly `README.md`, `LICENSE`, `LICENSE.md` or `LICENSE.txt` at the repo root. The match
  is case-sensitive. Everything else is gated, including `.gitattributes`, `readme.md`,
  `README.MD`, `README.txt`, `LICENSE.rst`, `license.txt`, `LICENCE`, `COPYING`, and `README.md` /
  `LICENSE.txt` in sub-folders. `/raw/` and `/blob/` are gated even for `README.md`. [OBS]
- **ACC-6** **Gate before existence.** For a non-allowlisted path, the gate is checked *before*
  the revision or file is resolved. An unknown branch or file in a gated repo returns the gate error,
  not 404. An allowlisted path that does not exist returns `404 EntryNotFound`. [OBS]
- **ACC-7** With `gated == false`, the repo behaves like any public repo. [DOC]
- **ACC-9** The tree listing (`GET /api/models/{id}/tree/{rev}/…`) is public (ACC-4), but for LFS
  files the `xetHash` and `lfs.oid` (sha256) are **masked as 64 `*`** for callers without access
  (anonymous, pending requester) and **shown** to callers with access (owner). The git `oid` and
  sizes are never masked. [OBS 2026-10-05, `observations/2026-10-05-tree-masking.md`]
- **ACC-10** `/raw/{rev}/{path}` applies the same gate and the same per-state messages as `resolve`
  (401 anonymous, 403 for pending), **without** the ACC-5 allowlist. With access it serves the file,
  e.g. `README.md` as text. [OBS 2026-10-05, tree-masking and anonymous probes]
- **ACC-8** The owner can revoke access at any time without notice, in either approval mode. [DOC]

## 4. Requester transitions

| From | Action | Mode | To | Evidence |
|---|---|---|---|---|
| no request | submit gate form (`POST /{id}/ask-access`) | auto | `accepted` (immediately) | [DOC] |
| no request | submit gate form | manual | `pending`, `timestamp` = submission time; response `303` → repo page | [DOC] [OBS] |
| `reset` | submit gate form again | manual | `pending` with a **new `timestamp`**; `reviewedAt` removed; gone from the `reset` list | [OBS 2026-10-05, W s5b] |
| `reset` | submit gate form again | auto | presumably `accepted` | [DOC-implied] |
| `rejected` | submit again | manual | `303`, **no change** (still `rejected`, same `reviewedAt`) | [DOC] [OBS 2026-10-05, C m7] |
| `pending` | submit again | manual | `303`, still `pending`; whether `timestamp`/`fields` change is unknown | [OBS] [Q-2] |
| `accepted` | submit again | any | unknown | [Q-2] |
| `pending` | self-cancel (`POST /api/models/{id}/user-access-request/cancel`) | manual | **no request** (deleted from every list and the report); `200 {"ok":true}` (REQ-7) | [OBS 2026-10-06, X c2] |
| `accepted` / `rejected` / `reset` / none | self-cancel | manual | **no change**; `404` (REQ-7) | [OBS 2026-10-06, X c1 c3 c4 c2-again] |

- **REQ-1** The requester must be logged in. Anonymous users see "Log in or Sign Up to review the
  conditions…". [DOC] [OBS]
- **REQ-2** `ask-access` **accepts a Bearer token** (tested with a write-role user token). JSON `{}` and
  form-encoded `{}` bodies both give `303` with `Location: https://huggingface.co/{id}` and no
  `X-Error-*` headers. The repo had no extra fields. [OBS 2026-10-05,
  `observations/2026-10-05-requester-ask-access.md`] The docs' "only from your browser" is
  therefore about the UI, not the endpoint. HTML pages do **not** honour Bearer tokens: the page
  renders with `isLoggedIn: false` even with the header. Read-role and fine-grained tokens,
  required-field validation, and anonymous posts are still untested [Q-1] [Q-16].
- **REQ-3** Submitting means agreeing to share **username + email** (plus the extra fields) with the
  repo authors. [DOC]
- **REQ-7** Self-cancel `POST /api/models/{id}/user-access-request/cancel` (no body) only withdraws a
  **pending** request, and deletes it: the four lists and the report no longer have it, and
  `auth-check` is back to "not in the authorized list" (a new `ask-access` then creates a new pending
  request). Success: `200`, JSON `{"ok":true}`. From `accepted`, `rejected` or `reset`, or with no
  request (the owner on their own repo too): `404`, `{"error":"No pending access request found for this
  repo and this user"}` with the same `X-Error-Message`, no `X-Error-Code`, and the request is unchanged
  (a rejected user cannot clear the rejection this way). Anonymous: `401` "Invalid username or
  password.". [OBS 2026-10-06, `observations/2026-10-06-requester-cancel.md` (X), and the UI walkthrough
  `observations/2026-10-06-ui-walkthrough.md`] Not recorded: whether HF's own pages show a control
  for it, and whether it e-mails anyone [Q-3].

## 5. Owner (reviewer) transitions

You need a token with **write** access to the repo (user owner, or write/admin org role). A read-only
token gets 403. [DOC] [CLIENT]

### 5.1 `POST …/user-access-request/handle` `{user|userId, status, rejectionReason?, resetReason?}`

Success → `200`, JSON body `{}`. [OBS 2026-10-05] Evidence for the table: W = `observations/2026-10-05-owner-walkthrough.md`,
C = `observations/2026-10-05-owner-walkthrough-completion.md`, plus the UI walkthrough (`observations/2026-10-05-ui-walkthrough.md`).
Re-observed on 2026-10-06 on the new sandbox `OwnerOfTheGatedModel/tiny-gated-model` (another owner
account) with the same cases (`harness/kb/probes/*.json`, `--var SANDBOX=…`): every status and
`X-Error-Message` matches, except W s0–s3b: the 2026-10-05 run started with no request (404 on
accept, cancel, reject), the 2026-10-06 one with a pending request, so there s1–s3 succeed (`200 {}`) and
s3b shows a re-request after a rejection leaving it rejected (as C m7). X =
`observations/2026-10-06-requester-cancel.md` (requester self-cancel, REQ-7).

| From \ To | `pending` ("Cancel") | `accepted` ("Accept") | `rejected` ("Reject") | `reset` |
|---|---|---|---|---|
| no request | 404 [OBS W s2] | 404 [OBS W s1] | 404 [OBS W s3] | ? |
| `pending` | **404** [OBS C m4] | ok [OBS C m1, UI] | ok [OBS C m5, UI] | ? [Q-5] |
| `accepted` | ok, user loses access [OBS C m3, UI] | **404** [OBS C m2] | ok [CLIENT tests] | ok [OBS W s5] |
| `rejected` | ok [CLIENT doc] | ok [OBS W s4, UI] | **404** [OBS C m6] | ok [OBS C m8] |
| `reset` | ? | ? | ? | ? [Q-5] |

Every **404** in this table is the same: `404`, no `X-Error-Code`, JSON `{"error": "No access request
found matching your criteria"}` with the same `X-Error-Message`.

- **REV-1** A same-status transition is an **error**, identical to "no request": the 404 above, not a
  no-op. (`batch` differs: see REV-9.) [OBS 2026-10-05]
- **REV-2** `rejectionReason`: optional, at most 200 characters, shown to the user. [DOC] [SPEC] 201 characters → `400`
  `* Too big: expected string to have <=200 characters * at rejectionReason`. [OBS] The reason is not
  returned by any API we observed (REQ-4). The Python client refuses a reason when
  `status != "rejected"` (client-side only); what the server does then is [Q-9].
- **REV-3** `reset`: revokes the previous decision; the user loses access and **receives an email**
  that includes the optional `resetReason` (at most 200 characters). The entry moves to the `reset` list
  (`reviewedAt` = reset time, no `grantedBy`, `timestamp` kept) until the user submits again. Reset
  works from `accepted` and from `rejected`. It differs from `pending` (keeps the request, back in the
  queue) and from `rejected` (blocks re-requests). [DOC] [OBS 2026-10-05]
- **REV-4** The `pending` list is **not** always empty in auto mode. Cancelling an accepted user
  puts them back in `pending` even when `gated == "auto"` [CLIENT tests], and switching manual → auto
  leaves pending requests pending [OBS, CFG-6].
- **REV-5** `user` is the username; `userId` (24-hex) is an alternative, and exactly one is required. `userId` works
  [OBS C m3]. Neither → `400 * Either userId or user must be provided, but not both`. [OBS]
- **REV-12** Validation errors are `400` with a zod-style `X-Error-Message`/`{"error"}`, no
  `X-Error-Code` [OBS 2026-10-05, W s7]:
  - invalid status → `* Invalid option: expected one of "accepted"|"rejected"|"pending"|"reset" * at status`;
  - unknown username → `404 User not found`;
  - a non-owner (requester token) → `403 You have read access but not the required permissions for this operation`.

### 5.2 `POST …/user-access-request/grant` `{user|userId}`

- **REV-6** Adds the user to `accepted` without them requesting. Their entry has no email. [CLIENT tests]
  Success → `200 {}`. [OBS]
- **REV-7** Granting a user who already has access → `400 That user already has access to the repo`
  [OBS W s6-grant-again] [CLIENT]. Unknown user → 404. Repo not gated → 400 per the client docstring
  [CLIENT doc], **unobserved**. The same docstring's "400 if not gated" is already contradicted for
  lists (CFG-6), so the clone answers normally (provisional, Q-9). The conformance suite keeps the
  docstring's claim as a strict expected failure (`divergences.yaml` D-4) until it is recorded.
- **REV-8** Granting a **pending** user accepts their request: `reviewedAt` = grant time,
  `grantedBy` = owner, `timestamp` and `email` kept (it is their own request). [OBS W s6] Granting
  `rejected` / `reset` users is unknown [Q-6].

### 5.3 `POST …/user-access-request/batch` `{status, rejectionReason?, resetReason?, requests: [{user|userId}] (1–100)}`

- **REV-9** Applies the same status (and reason) to up to 100 requests in one call. Returns a list
  **in input order** [SPEC]; observed items echo the identifier sent: `{"user": "TestingBOrig", "ok":
  true}`, `{"user": "<unknown>", "ok": false, "error": "user_not_found"}`. **Unlike `handle`, an item
  already in the target status is `ok: true`.** [OBS 2026-10-05, W s8]

### 5.4 Listing: `GET …/user-access-request/{pending|accepted|rejected|reset}`

- **REV-10** Query parameters: `limit` (10–1000, default 1000), `after` / `before` (ISO date-time,
  `Z`), and `q` (at most 250 characters), which searches username, fullname, email, email domain and verified org.
  Pagination uses a `Link: <…>; rel="next"` header. [SPEC] `limit=5` →
  `400 * Too small: expected number to be >=10 * at limit`; `q=testingb` matches `TestingBOrig`
  (case-insensitive prefix). [OBS 2026-10-05] Default ordering and the field `after`/`before` filter
  on are [Q-10] [Q-21].
- **REV-11** The Python client only knows 3 lists. It has no `reset` list and no batch. [CLIENT]

## 6. Timestamps

- **TS-1** `timestamp` = time of the submission that created the request (observed within ~60 ms of
  the `ask-access` call). A re-request after **reset** sets a new `timestamp`. Accept, cancel,
  reject, reset and grant never change it. [OBS 2026-10-05]
- **TS-2** `reviewedAt` = time of the last accept, reject, reset or grant (within ~60 ms of the call).
  Moving back to `pending` (cancel, batch) **removes** it. [OBS 2026-10-05]
- **TS-3** Whether a re-submit while pending changes `timestamp` is unknown [Q-2]. List ordering is [Q-10].

## 7. Side effects that are not HTTP responses

Real emails cannot be reproduced. The clone records them in an inspectable **outbox** instead.

| Trigger | Effect | Evidence |
|---|---|---|
| new request in **manual** mode | email to the notification recipient(s), real-time or daily digest | [DOC] |
| `reset` | email to the user, including `resetReason` | [DOC] |
| per-user preference `gated_user_access_request` (`PATCH /api/settings/notifications`) | turns the above notifications on or off for a user | [SPEC] |
| any status change | **no webhook event exists** for access requests (none in the webhooks docs) | [DOC] |

## 8. Access report

- **REP-1** `GET /{id}/user-access-report` downloads every request in every status. Each entry has
  `user`, `fullname`, `status`, `email`, `time` (initial request) and `reviewedAt` (unset when pending). [DOC]
  The response carries a `Content-Disposition` filename. [SPEC] Observed for the owner [OBS 2026-10-05,
  `observations/2026-10-05-owner-reads.md`]: `200`, `Content-Type: application/json` (no charset),
  `Content-Disposition: attachment; filename=user-access-report-{ns}-{name}.json`. The body is a JSON
  array; a pending entry is `{"fullname", "user", "email", "time", "status"}` in that order, with no
  `reviewedAt`. An accepted entry is `{"fullname", "user", "email", "time", "reviewedAt", "status",
  "grantedBy": {"fullname", "user"}}` in that order [OBS 2026-10-06, W s1]. A self-cancelled request is
  gone from it (REQ-7). Rejected and reset entries, and `fields`, are still [Q-14].
- **REP-2** Anonymous → 401 "Invalid username or password." [OBS]

## 9. Out of this spec

Gating Group Collections, EU / country blocking, Advanced Gating, datasets/spaces/kernels parity,
paid-plan gates and the Gemma special case: see [out-of-scope.md](out-of-scope.md).
