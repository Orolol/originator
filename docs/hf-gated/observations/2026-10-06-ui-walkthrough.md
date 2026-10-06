# Bridge exchange log: Scripted UI walkthrough (Playwright, web/e2e/walkthrough.ts) through the bridge, 2026-10-06

70 requests (15 state-changing), exported from the bridge by `harness/kb/bridge_log_to_md.py`. Every request below was fired by the web UI (or script) through the bridge to huggingface.co. E-mails redacted. Do not hand-edit.

| # | time (UTC) | persona | request | body | status | X-Error-Message / response |
|---|---|---|---|---|---|---|
| 313 | 14:01:49.936 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 314 | 14:01:49.938 | requester | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac3a4b8792f9017b6cb67ec", "name": "TestingBOrig", "full |
| 315 | 14:01:50.064 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been reset by the repo's authors. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to submit a new request. |
| 316 | 14:01:51.098 | requester | `POST /OwnerOfTheGatedModel/tiny-gated-model/ask-access` | {} | 303 | "See Other. Redirecting to https://huggingface.co/OwnerOfTheGatedModel/tiny-gate |
| 317 | 14:01:51.236 | requester | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac3a4b8792f9017b6cb67ec", "name": "TestingBOrig", "full |
| 318 | 14:01:51.234 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 319 | 14:01:51.350 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. |
| 320 | 14:01:51.671 | requester | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/cancel` |  | 200 | {"ok": true} |
| 321 | 14:01:51.800 | requester | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac3a4b8792f9017b6cb67ec", "name": "TestingBOrig", "full |
| 322 | 14:01:51.796 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 323 | 14:01:51.915 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted and you are not in the authorized list. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to ask for access. |
| 324 | 14:01:52.234 | requester | `POST /OwnerOfTheGatedModel/tiny-gated-model/ask-access` | {} | 303 | "See Other. Redirecting to https://huggingface.co/OwnerOfTheGatedModel/tiny-gate |
| 325 | 14:01:52.378 | requester | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac3a4b8792f9017b6cb67ec", "name": "TestingBOrig", "full |
| 326 | 14:01:52.376 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 327 | 14:01:52.549 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. |
| 328 | 14:01:52.891 | owner | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac4f4465de11a43eb34fb52", "name": "OwnerOfTheGatedModel |
| 329 | 14:01:52.889 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 330 | 14:01:53.006 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 331 | 14:01:53.932 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 332 | 14:01:53.936 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 333 | 14:01:53.942 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 334 | 14:01:54.529 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "accepted"} | 200 | {} |
| 335 | 14:01:55.713 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 336 | 14:01:55.724 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 337 | 14:01:55.710 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 338 | 14:01:56.261 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 339 | 14:01:56.264 | requester | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac3a4b8792f9017b6cb67ec", "name": "TestingBOrig", "full |
| 340 | 14:01:56.426 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 341 | 14:01:57.489 | requester | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` |  | 200 | "*.7z filter=lfs diff=lfs merge=lfs -text\n*.arrow filter=lfs diff=lfs merge=lfs |
| 342 | 14:01:57.826 | owner | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac4f4465de11a43eb34fb52", "name": "OwnerOfTheGatedModel |
| 343 | 14:01:57.824 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 344 | 14:01:57.938 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 345 | 14:01:58.775 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 346 | 14:01:58.792 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 347 | 14:01:58.796 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 348 | 14:01:59.422 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "pending"} | 200 | {} |
| 349 | 14:02:00.615 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 350 | 14:02:00.631 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 351 | 14:02:00.648 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 352 | 14:02:01.314 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "rejected"} | 200 | {} |
| 353 | 14:02:02.482 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 354 | 14:02:02.480 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 355 | 14:02:02.487 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 356 | 14:02:02.849 | requester | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac3a4b8792f9017b6cb67ec", "name": "TestingBOrig", "full |
| 357 | 14:02:02.848 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 358 | 14:02:02.964 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been rejected by the repo's authors. |
| 359 | 14:02:03.752 | owner | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac4f4465de11a43eb34fb52", "name": "OwnerOfTheGatedModel |
| 360 | 14:02:03.751 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 361 | 14:02:03.865 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 362 | 14:02:04.742 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 363 | 14:02:04.754 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 364 | 14:02:04.766 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 365 | 14:02:05.268 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "accepted"} | 200 | {} |
| 366 | 14:02:06.409 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 367 | 14:02:06.407 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 368 | 14:02:06.406 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 369 | 14:02:06.991 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "pending"} | 200 | {} |
| 370 | 14:02:08.123 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 371 | 14:02:08.119 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 372 | 14:02:08.121 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 373 | 14:02:08.598 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gated": "auto"} | 200 | {"gated": "auto"} |
| 374 | 14:02:08.884 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gated": "manual"} | 200 | {"gated": "manual"} |
| 375 | 14:02:09.231 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gatedNotificationsMode": "real-time"} | 200 | {} |
| 376 | 14:02:09.473 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gatedNotificationsMode": "bulk"} | 200 | {} |
| 377 | 14:02:09.736 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gated": false} | 200 | {"gated": false} |
| 378 | 14:02:10.070 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gated": "auto"} | 200 | {"gated": "auto"} |
| 379 | 14:02:10.328 | owner | `PUT /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | {"gated": "manual"} | 200 | {"gated": "manual"} |
| 380 | 14:02:10.609 | owner | `GET /api/whoami-v2` |  | 200 | {"type": "user", "id": "6ac4f4465de11a43eb34fb52", "name": "OwnerOfTheGatedModel |
| 381 | 14:02:10.602 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` |  | 200 | {"_id": "6ac4f6932fb5557d4ceee81f", "id": "OwnerOfTheGatedModel/tiny-gated-model |
| 382 | 14:02:10.736 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
