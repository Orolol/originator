# Probe results: harness/kb/probes/hf-gated-tree-masking.json

Recorded 2026-10-06T13:49:45Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| tree-subdir-anon | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 |  | [{"type":"file","oid":"1a78b7e6c35fa843b214689706ce9398ac8fc761","size":819,"path":"checkp | anonymous: LFS hashes masked? |
| tree-subdir-owner | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 |  | [{"type":"file","oid":"1a78b7e6c35fa843b214689706ce9398ac8fc761","size":819,"path":"checkp | owner (has access): masked? |
| tree-subdir-requester | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 |  | [{"type":"file","oid":"1a78b7e6c35fa843b214689706ce9398ac8fc761","size":819,"path":"checkp | requester (pending, no access): masked? |
| raw-readme-owner | HF_OWNER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 200 |  | --- license: mit ---  # tiny-gated-model  A tiny, randomly initialised GPT-2 (2 layers, 64 | /raw/ with access |
| raw-readme-requester | HF_REQUESTER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 403 | GatedRepo | Your request to access model OwnerOfTheGatedModel/tiny-gated-model is awaiting a review from the repo authors. | /raw/ pending requester |
| raw-readme-anon | anonymous | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 401 | GatedRepo | Access to model OwnerOfTheGatedModel/tiny-gated-model is restricted. You must have access to it and be authenticated to access it. Please log in. | /raw/ anonymous |
