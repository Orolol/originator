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
- **CFG-6** Effects of changing the mode while requests exist (manual→auto with pending
  requests, gated→false→gated) are **unknown**. [Q-7]

### Access request

There is at most one request per (repo, user). Shape as listed by the API [SPEC]:

| Field | Meaning | Evidence |
|---|---|---|
| `user` | requester profile: `user` (username), `fullname`, `_id` (24-hex ObjectId), `avatarUrl`, `isPro`, `type: "user"`, `verifiedOrgNames`, optional `email`, `orgs`, … | [SPEC] |
| `status` | `pending` \| `accepted` \| `rejected` \| `reset` | [SPEC] [DOC] |
| `fields` | answers to the gate form, map `label → string` | [SPEC] [CLIENT] |
| `timestamp` | when the user initially made the request (required) | [SPEC] [DOC] |
| `reviewedAt` | when accepted/rejected; unset for pending | [SPEC] [DOC] |
| `grantedBy` | user object of the granter, or `{}` | [SPEC]; when each form appears [Q-10] |

- **REQ-4** `rejectionReason` and `resetReason` are **not** in the list item schema
  (`additionalProperties: false`). The owner cannot read them back through the list API. [SPEC] [Q-19]
- **REQ-5** `user.email` is absent/`null` for users added through **grant**. The client test
  says: "email not shared when granted access manually". [CLIENT tests]

## 2. States and what they allow

"No request" is a real state: the user has never interacted, or the request was removed [Q-3].

| State | Can read gated files | Can (re)submit the form | Shown on repo page | Evidence |
|---|---|---|---|---|
| no request | no | yes (must be logged in) | consent form | [DOC] |
| `pending` | no; content routes answer `403 GatedRepo` "Your request to access model {id} is awaiting a review from the repo authors." | re-submitting is accepted silently (303), still `pending` | "awaiting review" message [Q-11] | [DOC] [OBS 2026-10-05] |
| `accepted` | **yes** | n/a | access granted | [DOC] |
| `rejected` | no | **no**, "cannot request access again" | "Your request to access this repo has been rejected by the repo's authors." + reason if any | [DOC] |
| `reset` | no | **yes**, prompted to agree and submit again on next visit | consent form again [Q-11] | [DOC] |

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
- **ACC-8** The owner can revoke access at any time without notice, in either approval mode. [DOC]

## 4. Requester transitions

| From | Action | Mode | To | Evidence |
|---|---|---|---|---|
| no request | submit gate form (`POST /{id}/ask-access`) | auto | `accepted` (immediately) | [DOC] |
| no request | submit gate form | manual | `pending`; response `303` → repo page | [DOC] [OBS 2026-10-05] |
| `reset` | submit gate form again | auto / manual | `accepted` / `pending` | [DOC-implied] [Q-5] |
| `rejected` | submit again | any | refused (exact response unknown) | [DOC] [Q-2] |
| `pending` | submit again | manual | `303` → repo page, still `pending`, no error. Whether `timestamp`/`fields` change is unknown | [OBS 2026-10-05] [Q-2] |
| `accepted` | submit again | any | unknown | [Q-2] |
| any | self-cancel (`POST /api/models/{id}/user-access-request/cancel`) | any | unknown (probably removes the request) | [SPEC] [Q-3] |

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

## 5. Owner (reviewer) transitions

You need a token with **write** access to the repo (user owner, or write/admin org role). A read-only
token gets 403. [DOC] [CLIENT]

### 5.1 `POST …/user-access-request/handle` `{user|userId, status, rejectionReason?, resetReason?}`

| From \ To | `pending` ("Cancel") | `accepted` ("Accept") | `rejected` ("Reject") | `reset` |
|---|---|---|---|---|
| no request | 404 request not found [CLIENT doc] | 404 [CLIENT doc] | 404 [CLIENT doc] | ? [Q-5] |
| `pending` | **error**, already pending [CLIENT tests; 404 per CLIENT doc] | ok [DOC] [CLIENT tests] | ok [DOC] [CLIENT tests] | ? [Q-5] |
| `accepted` | ok, user loses access [DOC] [CLIENT tests] | **error**, already accepted [CLIENT tests; 404 per doc] | ok [DOC] [CLIENT tests] | ok [DOC] |
| `rejected` | ok [CLIENT doc] | ok [CLIENT tests] | **error**, already rejected [CLIENT tests; 404 per doc] | ok? [DOC-implied] [Q-5] |
| `reset` | ? | ? | ? | ? [Q-5] |
| unknown username | 404 user not found [CLIENT doc] | | | |

- **REV-1** A same-status transition is an error, not a no-op. The client tests assert an HTTP error
  for accept→accepted, reject→rejected and cancel→pending. The status code (404 per docstrings) and
  the body are [Q-4].
- **REV-2** `rejectionReason`: optional, at most 200 characters, shown to the user. [DOC] [SPEC] The Python
  client refuses a reason when `status != "rejected"` (`ValueError`, client-side only). What the
  server does in that case is [Q-9].
- **REV-3** `reset`: revokes the previous decision; the user loses access and **receives an email**
  that includes the optional `resetReason` (at most 200 characters). Next visit, they must agree and submit
  again. It differs from `pending` (keeps the request, back in the queue) and from `rejected`
  (blocks re-requests). [DOC]
- **REV-4** The `pending` list is **not** always empty in auto mode. Cancelling an accepted user
  puts them back in `pending` even when `gated == "auto"`: the client integration test runs on an
  auto repo. The docs' "this list is empty unless manual" only describes the natural flow. [CLIENT tests] [DOC]
- **REV-5** `user` is the username; `userId` (24-hex) is an alternative, and one of them is required. [SPEC]

### 5.2 `POST …/user-access-request/grant` `{user|userId}`

- **REV-6** Adds the user to `accepted` without them requesting. Their entry has no email. [CLIENT tests]
- **REV-7** Granting a user who already has access → **400**. [CLIENT doc + tests] Unknown user →
  404. Repo not gated → 400. [CLIENT doc]
- **REV-8** Granting a user who is `pending`, `rejected` or `reset`: unknown. The response body is
  unknown too; the client returns `response.json()`. [Q-6]

### 5.3 `POST …/user-access-request/batch` `{status, rejectionReason?, resetReason?, requests: [{user|userId}] (1–100)}`

- **REV-9** Applies the same status (and reason) to up to 100 requests in one call. Returns a list of
  `{userId?, user?, ok, error?}` **in input order**, where `error ∈ {"user_not_found",
  "request_not_found"}`. [SPEC] How an item already in the target status is reported is [Q-4].

### 5.4 Listing: `GET …/user-access-request/{pending|accepted|rejected|reset}`

- **REV-10** Query parameters: `limit` (10–1000, default 1000), `after` / `before` (ISO date-time,
  `Z`), and `q` (at most 250 characters), which searches username, fullname, email, email domain and verified org.
  Pagination uses a `Link: <…>; rel="next"` header. [SPEC] Default ordering, which timestamp
  `after`/`before` filter on, and how `q` matches are all [Q-10] [Q-21].
- **REV-11** The Python client only knows 3 lists. It has no `reset` list and no batch. [CLIENT]

## 6. Timestamps

- **TS-1** `timestamp` is set when the user first requests. [DOC] [SPEC]
- **TS-2** `reviewedAt` is set when the request is accepted or rejected, and is absent for pending requests. [DOC]
- **TS-3** Whether cancel clears `reviewedAt`, whether a re-request after reset resets `timestamp`,
  and what `timestamp` a granted entry gets are all [Q-10].

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
  The response carries a `Content-Disposition` filename. [SPEC] The format (the docs say JSON;
  the spec says the body is a string), the filename, and whether `fields` are included are [Q-14].
- **REP-2** Anonymous → 401 "Invalid username or password." [OBS]

## 9. Out of this spec

Gating Group Collections, EU / country blocking, Advanced Gating, datasets/spaces/kernels parity,
paid-plan gates and the Gemma special case: see [out-of-scope.md](out-of-scope.md).
