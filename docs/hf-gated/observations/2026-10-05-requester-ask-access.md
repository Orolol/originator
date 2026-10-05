# Probe results: harness/kb/probes/hf-gated-requester-ask-access.json

Recorded 2026-10-05T13:32:01Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| pre-auth-check | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Access to model Orosius/deltanet-mla-latent is restricted and you are not in the authorized list. Visit https://huggingface.co/Orosius/deltanet-mla-latent to ask for access. | baseline: logged in, no request |
| pre-resolve | HF_REQUESTER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Access to model Orosius/deltanet-mla-latent is restricted and you are not in the authorized list. Visit https://huggingface.co/Orosius/deltanet-mla-latent to ask for access. | baseline file access |
| pre-head | HF_REQUESTER_ACCESS_TOKEN | `HEAD /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Access to model Orosius/deltanet-mla-latent is restricted and you are not in the authorized list. Visit https://huggingface.co/Orosius/deltanet-mla-latent to ask for access. | baseline HEAD |
| pre-owner-list | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 403 |  | You have read access but not the required permissions for this operation | owner endpoint with a non-owner write token |
| pre-page | HF_REQUESTER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent` | 200 |  |  | does the website honour Bearer tokens? |
| ask-access-json | HF_REQUESTER_ACCESS_TOKEN | `POST /Orosius/deltanet-mla-latent/ask-access (json {})` | 303 |  | Location: https://huggingface.co/Orosius/deltanet-mla-latent | Q-1: request access with a token, JSON body (repo has no extra fields) |
| post-json-auth-check | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. | state after JSON attempt |
| post-json-resolve | HF_REQUESTER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. | state after JSON attempt |
| ask-access-form | HF_REQUESTER_ACCESS_TOKEN | `POST /Orosius/deltanet-mla-latent/ask-access (form {})` | 303 |  | Location: https://huggingface.co/Orosius/deltanet-mla-latent | Q-1/Q-2: same with form encoding (re-submit if the first one worked) |
| post-form-auth-check | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. | state after form attempt |
| post-form-resolve | HF_REQUESTER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. | state after form attempt |

## Extracted component props

### pre-page

```json
{
 "gated": "manual",
 "isLoggedIn": false,
 "repoId": "Orosius/deltanet-mla-latent",
 "repoType": "model",
 "isGoogleGemma": false,
 "requiresPaidPlan": false
}
```

