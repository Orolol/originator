# Probe results: harness/kb/probes/hf-gated-clone-seed-reads.json

Recorded 2026-10-05T14:31:12Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| model-info-anon | anonymous | `GET /api/models/Orosius/deltanet-mla-latent` | 200 |  | {"_id":"69414ed409f9267fc5b494e2","id":"Orosius/deltanet-mla-latent","private":false,"tags | model info as seen anonymously (clone seed) |
| model-info-owner | HF_OWNER_ACCESS_TOKEN | `GET /api/models/Orosius/deltanet-mla-latent` | 200 |  | {"_id":"69414ed409f9267fc5b494e2","id":"Orosius/deltanet-mla-latent","private":false,"tags | model info as owner |
| model-info-expand | anonymous | `GET /api/models/Orosius/deltanet-mla-latent?expand[]=gated&expand[]=cardData` | 200 |  | {"_id":"69414ed409f9267fc5b494e2","id":"Orosius/deltanet-mla-latent","gated":"manual","car | expand[] selects fields |
| tree-main | anonymous | `GET /api/models/Orosius/deltanet-mla-latent/tree/main` | 200 |  | [{"type":"directory","oid":"45f7f8654f96b4ae8411aae127de9d8a4b4f90f9","size":0,"path":"che | top-level tree |
| tree-subdir | anonymous | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 |  | [{"type":"file","oid":"0a7ba649036761f60fc6500b85716c498875e5a2","size":1541,"path":"check | one checkpoint folder |
| whoami-owner | HF_OWNER_ACCESS_TOKEN | `GET /api/whoami-v2` | 200 |  | {"type":"user","id":"63ea055c74f940d171e52701","name":"Orosius","fullname":"Gaetan Martin" | owner identity |
| whoami-requester | HF_REQUESTER_ACCESS_TOKEN | `GET /api/whoami-v2` | 200 |  | {"type":"user","id":"6ac3a4b8792f9017b6cb67ec","name":"TestingBOrig","fullname":"Bridge"," | requester identity |
| whoami-anon | anonymous | `GET /api/whoami-v2` | 401 |  | Invalid username or password. | anonymous whoami |
| whoami-bad-token | BAD_TOKEN | `GET /api/whoami-v2` | 401 |  | Invalid username or password. | invalid token wording |
| owner-readme | HF_OWNER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/resolve/main/README.md` | 200 |  | --- license: mit ---  | README content + headers |
| owner-gitattributes | HF_OWNER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 |  | *.7z filter=lfs diff=lfs merge=lfs -text *.arrow filter=lfs diff=lfs merge=lfs -text *.bin | .gitattributes content + headers |
| owner-head-gitattributes | HF_OWNER_ACCESS_TOKEN | `HEAD /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 |  |  | HEAD headers of a small file |
| owner-head-lfs | HF_OWNER_ACCESS_TOKEN | `HEAD /Orosius/deltanet-mla-latent/resolve/main/checkpoint_tokens_20M_loss_4.9842/pytorch_model.bin` | 302 |  | Location: https://us.aws.cdn.hf.co/xet-bridge-us/69414ed409f9267fc5b494e2/0c6167a268354949eabb7862cdefe9b5759bdb481e9c523a24b36daf5e474f3e?<signed-query-redacted> | HEAD of an LFS file (redirect?) |
| owner-config | HF_OWNER_ACCESS_TOKEN | `GET /Orosius/deltanet-mla-latent/resolve/main/checkpoint_tokens_20M_loss_4.9842/config.json` | 200 |  | {   "model_type": "swa_mla",   "total_tokens": 20500480,   "val_loss": 4.984230031967163,  | a small JSON file in a subfolder |
| anon-readme | anonymous | `GET /Orosius/deltanet-mla-latent/resolve/main/README.md` | 200 |  | --- license: mit ---  | allowlisted anonymously (ACC-5) |
| anon-head-readme | anonymous | `HEAD /Orosius/deltanet-mla-latent/resolve/main/README.md` | 200 |  |  | HEAD allowlisted |
| anon-ask-access-get | anonymous | `GET /Orosius/deltanet-mla-latent/ask-access` | 404 |  | Sorry, we can't find the page you are looking for. | GET on the POST-only web route |
| owner-unknown-repo-list | HF_OWNER_ACCESS_TOKEN | `GET /api/models/Orosius/does-not-exist-xyz/user-access-request/pending` | 404 | RepoNotFound | Repository not found | owner list on a missing repo |
| owner-not-gated-list | HF_OWNER_ACCESS_TOKEN | `GET /api/models/openai-community/gpt2/user-access-request/pending` | 403 |  | You have read access but not the required permissions for this operation | list on someone else's non-gated repo |
