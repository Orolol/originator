# Probe results: harness/kb/probes/hf-gated-requester-ask-access.json

Recorded 2026-10-06T13:49:42Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| pre-auth-check | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 403 | GatedRepo | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted and you are not in the authorized list. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to ask for access. | baseline: logged in, no request |
| pre-resolve | HF_REQUESTER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 403 | GatedRepo | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted and you are not in the authorized list. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to ask for access. | baseline file access |
| pre-head | HF_REQUESTER_ACCESS_TOKEN | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 403 | GatedRepo | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted and you are not in the authorized list. Visit https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model to ask for access. | baseline HEAD |
| pre-owner-list | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 403 |  | You have read access but not the required permissions for this operation | owner endpoint with a non-owner write token |
| pre-page | HF_REQUESTER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model` | 200 |  |  | does the website honour Bearer tokens? |
| ask-access-json | HF_REQUESTER_ACCESS_TOKEN | `POST /OwnerOfTheGatedModel/tiny-gated-model/ask-access (json {})` | 303 |  | Location: https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model | Q-1: request access with a token, JSON body (repo has no extra fields) |
| post-json-auth-check | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. | state after JSON attempt |
| post-json-resolve | HF_REQUESTER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. | state after JSON attempt |
| ask-access-form | HF_REQUESTER_ACCESS_TOKEN | `POST /OwnerOfTheGatedModel/tiny-gated-model/ask-access (form {})` | 303 |  | Location: https://huggingface.co/OwnerOfTheGatedModel/tiny-gated-model | Q-1/Q-2: same with form encoding (re-submit if the first one worked) |
| post-form-auth-check | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. | state after form attempt |
| post-form-resolve | HF_REQUESTER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. | state after form attempt |

## Extracted component props

### pre-page

```json
{
 "gated": "manual",
 "isLoggedIn": false,
 "repoId": "OwnerOfTheGatedModel/tiny-gated-model",
 "repoType": "model",
 "isGoogleGemma": false,
 "requiresPaidPlan": false
}
```

