# Probe results: harness/kb/probes/hf-gated-reset-from-pending.json

Recorded 2026-10-06T14:44:41Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| r0-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| r0-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| r0-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| r0-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [] |  |
| r1-reset-from-pending | OWNER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle (json {"user": "TestingBOrig", "status": "reset", "resetReason": "confirm Q-5"})` | 200 |  | {} | Q-5 pending -> reset, again |
| r1-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [] |  |
| r1-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| r1-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| r1-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| r1b-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [] |  |
| r1b-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| r1b-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| r1b-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| r1-report | OWNER | `GET http://127.0.0.1:8100/OwnerOfTheGatedModel/tiny-gated-model/user-access-report` | 200 |  | [{"fullname":"Bridge","user":"TestingBOrig","email":"<email>","time":"2026-10-06T14:42:55. | is the reset-from-pending entry in the report? |
| r1-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been reset by the repo's authors. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to submit a new request. |  |
| r2-pending-from-reset | OWNER | `POST http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle (json {"user": "TestingBOrig", "status": "pending"})` | 200 |  | {} | restore pending |
| r2-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| r2-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| r2-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| r2-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [] |  |
