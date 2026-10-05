# Open-source client: `huggingface_hub` (and `huggingface.js`)

The server is closed source, but its official clients are not. They give three things:
1. a **typed surface** of the endpoints (what HF considers the supported API);
2. **docstrings listing the HTTP errors** per call (a cheap spec of the edge cases);
3. **integration tests that ran against a real Hub instance** (`hub-ci.huggingface.co`). These are
   our best evidence for state transitions short of observing them ourselves.

Pinned at `huggingface_hub@d699913` (2026-10-05), `src/huggingface_hub/hf_api.py`.

## 1. Gated-related API surface (`HfApi`)

| Method | HTTP | Notes |
|---|---|---|
| `update_repo_settings(repo_id, *, gated=None, private=None, visibility=None, repo_type=None)` | `PUT /api/{type}s/{id}/settings` | validates `gated ∈ {"auto","manual",False}` client-side; raises `ValueError("At least one setting must be updated.")` on an empty payload; **does not** expose `orgMembersGated` or the notification settings |
| `list_pending_access_requests(repo_id, *, repo_type, token)` | `GET …/user-access-request/pending` | generator; follows `Link rel=next` |
| `list_accepted_access_requests(…)` | `GET …/accepted` | |
| `list_rejected_access_requests(…)` | `GET …/rejected` | no `reset` list method |
| `accept_access_request(repo_id, user, …)` | `POST …/handle {user, status:"accepted"}` | |
| `reject_access_request(repo_id, user, *, rejection_reason, …)` | `POST …/handle {user, status:"rejected", rejectionReason?}` | `rejection_reason` is keyword-only with **no default** (`str \| None`), so callers must pass it, `None` included |
| `cancel_access_request(repo_id, user, …)` | `POST …/handle {user, status:"pending"}` | "cancel" = **back to pending**, not delete |
| `grant_access(repo_id, user, …)` | `POST …/grant {user}` | returns `response.json()` |
| `auth_check(repo_id, *, repo_type, token, write=False)` | `GET /api/{type}s/{id}/auth-check[/write]` | raises `GatedRepoError` / `RepositoryNotFoundError` |
| `model_info(…).gated`, `list_models(gated=…, expand=["gated"])` | metadata | `gated: Literal["auto","manual",False] \| None` |
| `file_exists(…)` | `HEAD` resolve | re-raises `GatedRepoError` instead of returning `False` |

`AccessRequest` dataclass: `username, fullname, email: str | None, timestamp: datetime,
status: Literal["pending","accepted","rejected"], fields: dict | None`.

### What the client does **not** cover (exists server-side per spec/docs)

- `reset` status: not in the `Literal`s, no `list_reset_access_requests`, no `reset_reason`.
- `batch` endpoint.
- `userId` addressing (the client always sends `user`).
- Requester actions: `ask-access`, self-cancel (`…/user-access-request/cancel`).
- `orgMembersGated`, `gatedNotificationsMode`, `gatedNotificationsEmail`.
- Access report download.
- `grantedBy`, `reviewedAt` and `user._id` are dropped when parsing.

## 2. Documented errors (docstrings)

For `list_*`, `accept`, `reject` and `cancel`: **400** repo not gated, **403** read-only access
(not write/admin in the org, or a `read` token). For `accept`/`reject`/`cancel` also: **404** user does
not exist, **404** access request cannot be found, **404** "already in the {accepted|rejected|pending}
list". For `grant_access`: 400 not gated, **400 user already has access**, 403 read-only, 404 user
does not exist.

## 3. Integration tests as recorded behaviour (`tests/test_hf_api.py::TestAccessRequestAPI`)

Run against staging (`hub-ci.huggingface.co`) on a repo set to `gated: "auto"`, with a second user:

1. A fresh gated repo has all three lists empty.
2. `grant_access(user)`, then accepted has 1 entry: `status == "accepted"`, **`email is None`**
   ("email not shared when granted access manually"), `timestamp` is a datetime.
3. `cancel_access_request`: accepted is empty, **pending has the user**, even in auto mode.
4. `reject_access_request(rejection_reason=…)`: pending is empty, rejected has the user.
5. `accept_access_request`: accepted has the user (rejected → accepted is allowed).
6. Errors: grant twice; accept when already accepted; reject when already rejected; cancel when
   already pending. Each raises `HfHubHTTPError` (the code is not asserted).
7. Setting `gated` to `"manual"`+`private`, then `False`+public, round-trips through `model_info`
   (`test_update_repo_settings`).
8. `auth_check` with another user's token on an auto-gated repo raises `GatedRepoError`.

The tests sleep 1 s after each write ("give the server time to propagate"), so **the real Hub
is eventually consistent** for these lists. Conformance scripts against the real Hub need the same
tolerance; the clone is consistent by construction.

Reusing these scenarios against the clone is a cheap conformance check (see `api.md` §4 for the
`HF_ENDPOINT` gotcha). **Do not** use the staging credentials from `tests/testing_constants.py`:
that is HF's CI infrastructure, not ours.

## 4. Error classes and CLI

- `GatedRepoError(RepositoryNotFoundError)`, selected by `X-Error-Code: GatedRepo`. Message
  prefix: `{status} Client Error.\n\nCannot access gated repo for url {url}.` followed by the server
  message.
- CLI (`hf`): `hf repos settings <id> --gated auto|manual|false`; `hf models ls --gated/--no-gated`.
  On a `GatedRepoError` the CLI prints `Access denied. Model '<id>' requires approval.`, or
  `Repository` when the repo type is unknown.

## 5. `huggingface.js` (`@huggingface/hub`, `huggingface.js@3064743`)

Read-only typings, with no access-request functions. Useful bits:
- `gated: false | "auto" | "manual"` on models, datasets and collection items;
- the card-metadata type lists the field types **including the undocumented `ip_location`**, plus
  `extra_gated_prompt/heading/description/button_content`.
