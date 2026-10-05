# HTTP contract: gated models

Wire-level reference. The clone must speak **this exact protocol** (paths, payloads, status codes,
`X-Error-*` headers), so that the official `huggingface_hub` client, our bridge and our scripts
drive the real Hub and the clone the same way. Rules (`REV-*`, `ACC-*`…) live in
[behaviour.md](behaviour.md). The machine-readable subset of HF's OpenAPI spec is in
[snapshots/openapi-gated.json](snapshots/openapi-gated.json).

Base URL: `https://huggingface.co`. Auth: `Authorization: Bearer <token>`. Datasets use the same
endpoints with `/api/datasets/…` and `/datasets/{ns}/{repo}/…`; the slice only covers models.

## 1. Endpoint inventory

### Owner side (token with write access to the repo)

| Method | Path | Body / query | Success | Evidence |
|---|---|---|---|---|
| `PUT` | `/api/models/{ns}/{repo}/settings` | `{gated?: false\|"auto"\|"manual", orgMembersGated?: bool, gatedNotificationsMode?: "bulk"\|"real-time", gatedNotificationsEmail?: email, private?, visibility?, discussionsDisabled?, discussionsSorting?}` | 200 + updated settings object | [SPEC] [CLIENT] |
| `GET` | `/api/models/{ns}/{repo}/user-access-request/{status}` | `status ∈ pending\|accepted\|rejected\|reset`; query `limit` (10–1000, default 1000), `after`, `before` (ISO `…Z`), `q` (≤250) | 200 + `AccessRequest[]`, `Link` header with `rel="next"` | [SPEC] [DOC] |
| `POST` | `/api/models/{ns}/{repo}/user-access-request/handle` | `{user\|userId, status: "accepted"\|"rejected"\|"pending"\|"reset", rejectionReason? (≤200), resetReason? (≤200)}` | 200, body unknown [Q-4] | [SPEC] [DOC] |
| `POST` | `/api/models/{ns}/{repo}/user-access-request/grant` | `{user\|userId}` | 200, JSON body unknown [Q-6] | [SPEC] [CLIENT] |
| `POST` | `/api/models/{ns}/{repo}/user-access-request/batch` | `{status, rejectionReason?, resetReason?, requests: [{user\|userId}] (1–100)}` | 200 + `[{userId?, user?, ok, error?: "user_not_found"\|"request_not_found"}]` in input order | [SPEC] |
| `GET` | `/{ns}/{repo}/user-access-report` | none | 200 + file, `Content-Disposition` filename | [SPEC] [DOC] |

Note that the access report lives on the **web** route (`/{ns}/{repo}/…`), not under `/api`.

### Requester side

| Method | Path | Body | Success | Evidence |
|---|---|---|---|---|
| `POST` | `/{ns}/{repo}/ask-access` | object `{<field label>: <value>, …}` (keys = `extra_gated_fields` labels), JSON **or** form-encoded | **303**, `Location: https://huggingface.co/{ns}/{repo}` (absolute), no body of interest | [SPEC] [OBS 2026-10-05] |
| `POST` | `/api/models/{ns}/{repo}/user-access-request/cancel` | none | unknown [Q-3] | [SPEC] |

`ask-access` is a web route, but it **accepts `Authorization: Bearer`**. It was observed with a
write-role user token on a manual repo with no extra fields; JSON and form bodies behave the same,
and a re-submit while pending also gives 303. [OBS 2026-10-05] HTML pages, by contrast, ignore
Bearer tokens (`isLoggedIn: false`), so the logged-in **screens** can only be recorded with a real
browser session. Still unknown: read-role and fine-grained tokens, anonymous posts, and missing
required fields [Q-1] [Q-16].

### Public reads used by the slice

| Method | Path | Notes | Evidence |
|---|---|---|---|
| `GET` | `/api/models/{ns}/{repo}` (`?expand[]=gated&expand[]=cardData`) | `gated: false\|"auto"\|"manual"`, `cardData.extra_gated_*`; public on gated repos | [OBS] [CLIENT] |
| `GET` | `/api/models?gated=true\|false&expand[]=gated` | listing filter | [CLIENT] |
| `GET` | `/api/models/{ns}/{repo}/auth-check` (and `/auth-check/write`) | 200 `OK` if the caller can read; gate error otherwise | [CLIENT] [OBS] |
| `GET`/`HEAD` | `/{ns}/{repo}/resolve/{rev}/{path}` | file download; gate applies (allowlist ACC-5) | [OBS] |
| `GET` | `/{ns}/{repo}/raw/{rev}/{path}`, `/{ns}/{repo}/blob/{rev}/{path}` | gated, no allowlist | [OBS] |
| `GET` | `/api/models/{ns}/{repo}/tree/{rev}` | public listing | [OBS] |

## 2. `AccessRequest` list item (response of the list endpoint)

```jsonc
{
  "user": {                       // required fields: _id, avatarUrl, fullname, isPro, user, type, verifiedOrgNames
    "_id": "24-hex ObjectId",
    "user": "username",
    "fullname": "Full Name",
    "avatarUrl": "…",
    "isPro": false,
    "type": "user",
    "verifiedOrgNames": [],
    "email": "…",                 // optional; absent/null for granted users (REQ-5)
    "orgs": [{"id", "name", "fullname", "avatarUrl"}]   // optional, plus num* counters, details, …
  },
  "grantedBy": { /* user object */ } | {},
  "status": "pending" | "accepted" | "rejected" | "reset",   // required
  "fields": { "<label>": "<string>" },                       // only if the gate form has extra fields
  "timestamp": "2026-10-05T12:00:00.000Z",                   // required
  "reviewedAt": "2026-10-05T12:05:00.000Z"                   // absent while pending
}
```

`additionalProperties: false`: no `rejectionReason` and no `resetReason` in list items. [SPEC]

Observed pending entry (owner token, 2026-10-05, repo with no extra fields) [OBS]:
`{"user": {"_id", "avatarUrl": "/avatars/<hash>.svg", "isPro", "fullname", "user", "type": "user",
"verifiedOrgNames": [], "email"}, "timestamp": "2026-10-05T13:31:55.250Z", "status": "pending"}`.
It has **no** `fields`, `reviewedAt` or `grantedBy` keys. The keys appear in that order, and
`avatarUrl` is a relative path. A single page has no `Link` header.

How the Python client maps it (it drops `grantedBy`, `reviewedAt` and `_id`): `username=user.user`,
`fullname=user.fullname`, `email=user.get("email")`, `status`, `timestamp`, `fields`. [CLIENT]

## 3. Errors

The Hub reports errors with **headers**: `X-Error-Code` (machine-readable class) and
`X-Error-Message` (human text). The body is `text/plain` (the same message) on web routes like
`/resolve/`, and JSON `{"error": "<message>"}` on `/api/…`. 401 responses add
`WWW-Authenticate: Bearer realm="Authentication required", charset="UTF-8"`. [OBS]
`Access-Control-Expose-Headers` lists `X-Error-Code`, `X-Error-Message`, `Link`, `X-Request-Id`,
`X-Repo-Commit`, `X-Total-Count`, … which matters for a browser front end reading them. [OBS]

`huggingface_hub` classifies errors **from `X-Error-Code`**, so the clone must send it or the
client raises the wrong exception class:

| `X-Error-Code` | Client exception |
|---|---|
| `GatedRepo` | `GatedRepoError` (subclass of `RepositoryNotFoundError`) |
| `RepoNotFound`, or a 401 on a repo URL without a code (unless the message is "Invalid credentials in Authorization header") | `RepositoryNotFoundError` |
| `EntryNotFound` | `RemoteEntryNotFoundError` |
| `RevisionNotFound` | `RevisionNotFoundError` |
| none + 400 | `BadRequestError` |
| none + 403 | `HfHubHTTPError` ("403 Forbidden: {X-Error-Message}") |

### 3.1 Gate errors on content routes (`resolve`, `raw`, `blob`, `auth-check`)

| Caller | Status | `X-Error-Code` | Message (`{id}` = `ns/repo`) | Evidence |
|---|---|---|---|---|
| anonymous | **401** | `GatedRepo` | `Access to model {id} is restricted. You must have access to it and be authenticated to access it. Please log in.` | [OBS] |
| logged in, no request | **403** | `GatedRepo` | `Access to model {id} is restricted and you are not in the authorized list. Visit https://huggingface.co/{id} to ask for access.` | [OBS 2026-10-05: `auth-check`, `resolve` GET+HEAD] [CLIENT doc] |
| logged in, `pending` | **403** | `GatedRepo` | `Your request to access model {id} is awaiting a review from the repo authors.` | [OBS 2026-10-05: `auth-check`, `resolve`] |
| logged in, `rejected` | ? [Q-8] | ? | unknown via API. The web page says `Your request to access this repo has been rejected by the repo's authors.` | [DOC] [OBS-3P] |
| logged in, `reset` | ? [Q-8] | ? | unknown | |

For datasets the message says `dataset` instead of `model`, and the URL is `https://huggingface.co/datasets/{id}`. [OBS-3P]

### 3.2 Comparison cases

| Situation | Status | `X-Error-Code` | Message | Evidence |
|---|---|---|---|---|
| unknown repo, anonymous (`resolve` or `auth-check`) | 401 | none | `Invalid username or password.` | [OBS] |
| allowlisted path that does not exist in a gated repo | 404 | `EntryNotFound` | `Entry not found` | [OBS] |
| non-allowlisted unknown file or branch in a gated repo, anonymous | 401 | `GatedRepo` | gate message (ACC-6) | [OBS] |
| public repo `auth-check`, anonymous | 200 | none | body `OK` | [OBS] |

### 3.3 Owner endpoints

| Situation | Status | Evidence |
|---|---|---|
| anonymous (any owner endpoint, gated or not, and the report) | 401, `Invalid username or password.`, no `X-Error-Code` | [OBS] |
| repo not gated | 400 | [CLIENT doc] |
| read-only token / no write role | 403 | [CLIENT doc] |
| another user (write-role token, but no permission on this repo), list endpoint | 403, no `X-Error-Code`, `You have read access but not the required permissions for this operation` (JSON `{"error": …}`). "read access" refers to the user's permission on the repo, not the token role. | [OBS 2026-10-05] |
| unknown user | 404 | [CLIENT doc] |
| request not found | 404 | [CLIENT doc] |
| request already in the target list | 404 per docstring; tests only assert "an HTTP error" | [CLIENT] [Q-4] |
| grant to a user who already has access | 400 | [CLIENT doc + tests] |
| `rejectionReason` / `resetReason` longer than 200, bad `status`, `limit` out of range | probably 400 (schema violation) | [SPEC] [Q-9] |

The exact bodies and `X-Error-Message` strings for the owner-side errors still need to be recorded [Q-9].

## 4. Client-side gotchas (for conformance drivers)

- `huggingface_hub` builds the access-request URLs (`list_*`, `accept/reject/cancel_access_request`,
  `grant_access`) from the **module constant `constants.ENDPOINT`**, not from `HfApi(endpoint=…)`.
  To point those calls at the clone, set `HF_ENDPOINT=http://127.0.0.1:<port>` **before importing**
  `huggingface_hub`. `update_repo_settings` and `auth_check` do use `self.endpoint`. [CLIENT]
- `list_*` follows `Link: rel="next"` through `paginate()` with `http_backoff`. [CLIENT]
- The client's 401-on-repo-URL heuristic only applies when the URL matches its repo-API regex; send
  explicit `X-Error-Code`s rather than relying on it.
