# Probe results: harness/kb/probes/hf-gated-owner-walkthrough-completion.json

Recorded 2026-10-05T14:19:25Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| m0-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| m0-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 |  | [] |  |
| m0-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 |  | [] |  |
| m0-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 |  | [] |  |
| m0-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. |  |
| m0-req-resolve | REQUESTER | `GET http://127.0.0.1:8100/Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. |  |
| m1-accept | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"user": "TestingBOrig", "status": "accepted"})` | 200 |  | {} | pending -> accepted |
| m1-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 |  | [] |  |
| m1-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| m1-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 |  | [] |  |
| m1-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 |  | [] |  |
| m1-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/auth-check` | 200 |  | OK |  |
| m1-req-resolve | REQUESTER | `GET http://127.0.0.1:8100/Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 |  | *.7z filter=lfs diff=lfs merge=lfs -text *.arrow filter=lfs diff=lfs merge=lfs -text *.bin |  |
| m2-accept-again | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"user": "TestingBOrig", "status": "accepted"})` | 404 |  | No access request found matching your criteria | Q-4 same-status (accepted) |
| m3-cancel-by-userid | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"userId": "6ac3a4b8792f9017b6cb67ec", "status": "pending"})` | 200 |  | {} | accepted -> pending, addressed by userId (REV-5) |
| m3-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| m3-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 |  | [] |  |
| m3-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 |  | [] |  |
| m3-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 |  | [] |  |
| m3-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. |  |
| m3-req-resolve | REQUESTER | `GET http://127.0.0.1:8100/Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. |  |
| m4-cancel-again | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"user": "TestingBOrig", "status": "pending"})` | 404 |  | No access request found matching your criteria | Q-4 same-status (pending) |
| m5-reject | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"user": "TestingBOrig", "status": "rejected", "rejectionReason": "Rejected by the originator bridge walkthrough (test)."})` | 200 |  | {} | pending -> rejected with reason |
| m5-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 |  | [] |  |
| m5-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 |  | [] |  |
| m5-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| m5-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 |  | [] |  |
| m5-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent has been rejected by the repo's authors. |  |
| m5-req-resolve | REQUESTER | `GET http://127.0.0.1:8100/Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent has been rejected by the repo's authors. |  |
| m6-reject-again | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"user": "TestingBOrig", "status": "rejected"})` | 404 |  | No access request found matching your criteria | Q-4 same-status (rejected) |
| m7-req-ask-after-reject | REQUESTER | `POST http://127.0.0.1:8100/Orosius/deltanet-mla-latent/ask-access (json {})` | 303 |  | Location: http://127.0.0.1:8100/Orosius/deltanet-mla-latent | Q-2 re-request after rejection |
| m7-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 |  | [] |  |
| m7-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 |  | [] |  |
| m7-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| m7-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 |  | [] |  |
| m7-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent has been rejected by the repo's authors. |  |
| m7-req-resolve | REQUESTER | `GET http://127.0.0.1:8100/Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent has been rejected by the repo's authors. |  |
| m8-reset-from-rejected | OWNER | `POST http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/handle (json {"user": "TestingBOrig", "status": "reset", "resetReason": "Reset by the originator bridge walkthrough (test)."})` | 200 |  | {} | Q-5 reset from rejected |
| m8-list-pending | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 |  | [] |  |
| m8-list-accepted | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 |  | [] |  |
| m8-list-rejected | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 |  | [] |  |
| m8-list-reset | OWNER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 |  | [{"user":{"_id":"6ac3a4b8792f9017b6cb67ec","avatarUrl":"/avatars/eccbd8a248c3753b1ba445d9b |  |
| m8-req-auth-check | REQUESTER | `GET http://127.0.0.1:8100/api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent has been reset by the repo's authors. Visit https://huggingface.co/Orosius/deltanet-mla-latent to submit a new request. |  |
| m8-req-resolve | REQUESTER | `GET http://127.0.0.1:8100/Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent has been reset by the repo's authors. Visit https://huggingface.co/Orosius/deltanet-mla-latent to submit a new request. |  |
