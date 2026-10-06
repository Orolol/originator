# Bridge exchange log: Edge-case probe, part A (harness/kb/probes/hf-gated-edge-cases.json, cases e0 to e10-blob-missing-owner), exported from the bridge log: probe.py stopped at the next case on a dropped connection, before writing its own output

82 requests (15 state-changing), exported from the bridge by `harness/kb/bridge_log_to_md.py`. Every request below was fired by the web UI (or script) through the bridge to huggingface.co. E-mails redacted. Do not hand-edit.

| # | time (UTC) | persona | request | body | status | X-Error-Message / response |
|---|---|---|---|---|---|---|
| 447 | 14:40:36.364 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 448 | 14:40:36.480 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 449 | 14:40:36.591 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 450 | 14:40:36.729 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 451 | 14:40:36.844 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. |
| 452 | 14:40:36.957 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending?q=orig` |  | 200 | [] |
| 453 | 14:40:37.070 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending?q=TESTINGB` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 454 | 14:40:37.184 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending?q=testingborig` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 455 | 14:40:37.297 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending?q=bridge` |  | 200 | [] |
| 456 | 14:40:37.412 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending?q=t` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 457 | 14:40:37.527 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending?q=xyz` |  | 200 | [] |
| 458 | 14:40:37.641 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "reset", "resetReason": "edge-case probe"} | 200 | {} |
| 459 | 14:40:38.760 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 460 | 14:40:38.872 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 461 | 14:40:38.981 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 462 | 14:40:39.091 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 463 | 14:40:39.201 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been reset by the repo's authors. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to submit a new request. |
| 464 | 14:40:39.309 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "accepted"} | 200 | {} |
| 465 | 14:40:40.437 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 466 | 14:40:40.551 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 467 | 14:40:40.668 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 468 | 14:40:40.781 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 469 | 14:40:40.895 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 470 | 14:40:41.004 | requester | `POST /OwnerOfTheGatedModel/tiny-gated-model/ask-access` | {} | 303 | "See Other. Redirecting to https://huggingface.co/OwnerOfTheGatedModel/tiny-gate |
| 471 | 14:40:42.132 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 472 | 14:40:42.243 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 473 | 14:40:42.354 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 474 | 14:40:42.463 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 475 | 14:40:42.578 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 476 | 14:40:42.692 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "reset", "resetReason": "edge-case probe"} | 200 | {} |
| 477 | 14:40:42.805 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "rejected"} | 200 | {} |
| 478 | 14:40:43.922 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 479 | 14:40:44.033 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 480 | 14:40:44.140 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 481 | 14:40:44.254 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 482 | 14:40:44.367 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been rejected by the repo's authors. |
| 483 | 14:40:45.476 | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/user-access-report` |  | 200 | [{"fullname": "Bridge", "user": "TestingBOrig", "email": "<email>", "time": "202 |
| 484 | 14:40:45.589 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/grant` | {"user": "TestingBOrig"} | 200 | {} |
| 485 | 14:40:46.705 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 486 | 14:40:46.818 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 487 | 14:40:46.932 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 488 | 14:40:47.042 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 489 | 14:40:47.155 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 490 | 14:40:47.291 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "reset", "resetReason": "edge-case probe"} | 200 | {} |
| 491 | 14:40:48.456 | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/user-access-report` |  | 200 | [{"fullname": "Bridge", "user": "TestingBOrig", "email": "<email>", "time": "202 |
| 492 | 14:40:48.569 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/grant` | {"user": "TestingBOrig"} | 200 | {} |
| 493 | 14:40:49.693 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 494 | 14:40:49.807 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 495 | 14:40:49.923 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 496 | 14:40:50.035 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 497 | 14:40:50.150 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 498 | 14:40:50.262 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "reset", "resetReason": "edge-case probe"} | 200 | {} |
| 499 | 14:40:50.379 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "pending"} | 200 | {} |
| 500 | 14:40:51.499 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 501 | 14:40:51.613 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 502 | 14:40:51.724 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 503 | 14:40:51.847 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 504 | 14:40:51.960 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. |
| 505 | 14:40:52.068 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "accepted", "rejectionReason": "should be ignored?"} | 200 | {} |
| 506 | 14:40:53.186 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 507 | 14:40:53.300 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 508 | 14:40:53.411 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 509 | 14:40:53.569 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [] |
| 510 | 14:40:53.680 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 511 | 14:40:53.837 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/handle` | {"user": "TestingBOrig", "status": "reset"} | 200 | {} |
| 512 | 14:40:54.958 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 513 | 14:40:55.069 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [] |
| 514 | 14:40:55.200 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 515 | 14:40:55.312 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 516 | 14:40:55.426 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been reset by the repo's authors. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to submit a new request. |
| 517 | 14:40:55.579 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/grant` | {"user": "OwnerOfTheGatedModel"} | 200 | {} |
| 518 | 14:40:55.701 | owner | `POST /OwnerOfTheGatedModel/tiny-gated-model/ask-access` | {} | 303 | "See Other. Redirecting to https://huggingface.co/OwnerOfTheGatedModel/tiny-gate |
| 519 | 14:40:56.844 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` |  | 200 | [] |
| 520 | 14:40:57.135 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` |  | 200 | [{"user": {"_id": "6ac4f4465de11a43eb34fb52", "avatarUrl": "/avatars/cad5ae6b479 |
| 521 | 14:40:57.250 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` |  | 200 | [] |
| 522 | 14:40:57.367 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` |  | 200 | [{"user": {"_id": "6ac3a4b8792f9017b6cb67ec", "avatarUrl": "/avatars/eccbd8a248c |
| 523 | 14:40:57.480 | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 403 | Your request to access model OwnerOfTheGatedModel/tiny-gated-model has been reset by the repo's authors. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to submit a new request. |
| 524 | 14:40:57.591 | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` |  | 200 | "OK" |
| 525 | 14:40:57.700 | owner | `POST /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/cancel` |  | 404 | No pending access request found for this repo and this user |
| 526 | 14:40:57.813 | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/checkpoint-0/model.safetensors` |  | 200 | "version https://git-lfs.github.com/spec/v1\noid sha256:321019a3b5ea40a247b2cd8d |
| 527 | 14:40:57.932 | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/no-such-file.txt` |  | 404 | Entry not found |
| 528 | 14:40:58.039 | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/blob/main/no-such-file.txt` |  | 401 | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted. You must have access to it and be authenticated to access it. Please log in. |
