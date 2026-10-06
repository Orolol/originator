# Probe results: harness/kb/probes/hf-gated-owner-reads.json

Recorded 2026-10-06T13:49:44Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Post-processed: 2026-10-06: HF_REQUESTER_LOGIN held the public username TestingBOrig (not an e-mail) when this was recorded, so probe.py redacted the username itself; every <HF_REQUESTER_LOGIN> was then restored to TestingBOrig (lossless: the placeholder stands for that exact string, no token or e-mail involved). Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| owner-list-pending | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b | requester pending since 2026-10-05 |
| owner-list-accepted | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 |  | [] |  |
| owner-list-rejected | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 |  | [] |  |
| owner-list-reset | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 |  | [] |  |
| owner-report | HF_OWNER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/user-access-report` | 200 |  | [{"fullname":"Bridge","user":"TestingBOrig","email":"<email>","time":"2026-10-06T1 | Q-14 format |
| owner-auth-check | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 200 |  | OK | owner bypasses (ACC-1) |
| owner-get-settings | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | 404 |  | Sorry, we can't find the page you are looking for. | no GET settings (CFG-3) |
| owner-resolve | HF_OWNER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 200 |  | *.7z filter=lfs diff=lfs merge=lfs -text *.arrow filter=lfs diff=lfs merge=lfs -text *.bin | owner downloads gated file |
