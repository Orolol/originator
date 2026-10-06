# Probe results: harness/kb/probes/hf-gated-edge-cases-b.json

Recorded 2026-10-06T14:42:56Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| f0-owner-to-pending | OWNER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle (json {"user": "OwnerOfTheGatedModel", "status": "pending"})` | 200 |  | {} | cleanup of e8 (self-grant): owner's own entry back to pending |
| f0-owner-cancel | OWNER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/cancel` | 200 |  | {"ok":true} | cleanup: owner withdraws it (REQ-7), so it leaves every list |
| f0-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [] |  |
| f0-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| f0-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| f0-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| e10-head-raw-owner | HF_OWNER_ACCESS_TOKEN | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 200 |  |  | Q-27 HEAD raw (direct: the bridge routes GET only) |
| e10-head-raw-anon | anonymous | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/raw/main/.gitattributes` | 401 | GatedRepo | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted. You must have access to it and be authenticated to access it. Please log in. | Q-27 HEAD raw anonymous on a gated file |
| e10-head-blob-owner | HF_OWNER_ACCESS_TOKEN | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/blob/main/README.md` | 200 |  |  | Q-27 HEAD blob |
| e11-ask | REQUESTER | `POST http://127.0.0.1:8100/OwnerOfTheGatedModel/tiny-gated-model/ask-access (json {})` | 303 |  | Location: http://127.0.0.1:8100/OwnerOfTheGatedModel/tiny-gated-model | back to pending (after reset) |
| e11-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| e11-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| e11-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| e11-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [] |  |
| e11-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. |  |
| e12-to-false | OWNER | `PUT http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/settings (json {"gated": false})` | 200 |  | {"gated":false} | gated -> false with a pending request |
| e12-grant-not-gated | OWNER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/grant (json {"user": "TestingBOrig"})` | 400 | RepoNotGated | model OwnerOfTheGatedModel/tiny-gated-model is not gated | D-4 / REV-7: grant on a non-gated repo (400 per the client docstring?) |
| e12-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| e12-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| e12-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| e12-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [] |  |
| e12-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 200 |  | OK |  |
| e12-raw-anon-not-gated | anonymous | `GET http://127.0.0.1:8100/OwnerOfTheGatedModel/tiny-gated-model/raw/main/.gitattributes` | 200 |  | *.7z filter=lfs diff=lfs merge=lfs -text *.arrow filter=lfs diff=lfs merge=lfs -text *.bin | Q-27 /raw/ anonymous on a non-gated repo (200 or 307?) |
| e12-cancel | REQUESTER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/cancel` | 200 |  | {"ok":true} | remove the request if still pending (REQ-7) |
| e12-list-pending-empty | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [] | Q-9 list on a non-gated repo; empty if the cancel worked |
| e12-handle-not-gated | OWNER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle (json {"user": "TestingBOrig", "status": "rejected"})` | 400 | RepoNotGated | model OwnerOfTheGatedModel/tiny-gated-model is not gated | Q-9 handle on a non-gated repo |
| e13-to-manual | OWNER | `PUT http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/settings (json {"gated": "manual"})` | 200 |  | {"gated":"manual"} | restore manual |
| e13-ask | REQUESTER | `POST http://127.0.0.1:8100/OwnerOfTheGatedModel/tiny-gated-model/ask-access (json {})` | 303 |  | Location: http://127.0.0.1:8100/OwnerOfTheGatedModel/tiny-gated-model | end state: pending |
| e13-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| e13-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| e13-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| e13-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [] |  |
| e13-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. |  |
