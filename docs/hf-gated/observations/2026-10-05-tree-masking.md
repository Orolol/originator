# Probe results: harness/kb/probes/hf-gated-tree-masking.json

Recorded 2026-10-05T15:08:01Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| tree-subdir-anon | anonymous | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 |  | [{"type":"file","oid":"0a7ba649036761f60fc6500b85716c498875e5a2","size":1541,"path":"check | anonymous: LFS hashes masked? |
| tree-subdir-owner | HF_OWNER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 |  | [{"type":"file","oid":"0a7ba649036761f60fc6500b85716c498875e5a2","size":1541,"path":"check | owner (has access): masked? |
| tree-subdir-requester | HF_REQUESTER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 |  | [{"type":"file","oid":"0a7ba649036761f60fc6500b85716c498875e5a2","size":1541,"path":"check | requester (pending, no access): masked? |
| raw-readme-owner | HF_OWNER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/raw/main/README.md` | 200 |  | --- license: mit ---  | /raw/ with access |
| raw-readme-requester | HF_REQUESTER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/raw/main/README.md` | 403 | GatedRepo | Your request to access model Orosius/deltanet-mla-latent is awaiting a review from the repo authors. | /raw/ pending requester |
| raw-readme-anon | anonymous | `GET /Orosius/deltanet-mla-latent/raw/main/README.md` | 401 | GatedRepo | Access to model Orosius/deltanet-mla-latent is restricted. You must have access to it and be authenticated to access it. Please log in. | /raw/ anonymous |
