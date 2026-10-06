# Probe results: harness/kb/probes/hf-gated-clone-seed-reads.json

Recorded 2026-10-06T13:49:33Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Post-processed: 2026-10-06: HF_REQUESTER_LOGIN held the public username TestingBOrig (not an e-mail) when this was recorded, so probe.py redacted the username itself; every <HF_REQUESTER_LOGIN> was then restored to TestingBOrig (lossless: the placeholder stands for that exact string, no token or e-mail involved). Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| model-info-anon | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` | 200 |  | {"_id":"6ac4f6932fb5557d4ceee81f","id":"OwnerOfTheGatedModel/tiny-gated-model","private":f | model info as seen anonymously (clone seed) |
| model-info-owner | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` | 200 |  | {"_id":"6ac4f6932fb5557d4ceee81f","id":"OwnerOfTheGatedModel/tiny-gated-model","private":f | model info as owner |
| model-info-expand | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model?expand[]=gated&expand[]=cardData` | 200 |  | {"_id":"6ac4f6932fb5557d4ceee81f","id":"OwnerOfTheGatedModel/tiny-gated-model","gated":"ma | expand[] selects fields |
| tree-main | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main` | 200 |  | [{"type":"directory","oid":"05c7a8877e37d8cefdc36a9b918bf77f187f3ed6","size":0,"path":"che | top-level tree |
| tree-subdir | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 |  | [{"type":"file","oid":"1a78b7e6c35fa843b214689706ce9398ac8fc761","size":819,"path":"checkp | one checkpoint folder |
| whoami-owner | HF_OWNER_ACCESS_TOKEN | `GET /api/whoami-v2` | 200 |  | {"type":"user","id":"6ac4f4465de11a43eb34fb52","name":"OwnerOfTheGatedModel","fullname":"O | owner identity |
| whoami-requester | HF_REQUESTER_ACCESS_TOKEN | `GET /api/whoami-v2` | 200 |  | {"type":"user","id":"6ac3a4b8792f9017b6cb67ec","name":"TestingBOrig","fullname":"B | requester identity |
| whoami-anon | anonymous | `GET /api/whoami-v2` | 401 |  | Invalid username or password. | anonymous whoami |
| whoami-bad-token | BAD_TOKEN | `GET /api/whoami-v2` | 401 |  | Invalid username or password. | invalid token wording |
| owner-readme | HF_OWNER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/README.md` | 200 |  | --- license: mit ---  # tiny-gated-model  A tiny, randomly initialised GPT-2 (2 layers, 64 | README content + headers |
| owner-gitattributes | HF_OWNER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 200 |  | *.7z filter=lfs diff=lfs merge=lfs -text *.arrow filter=lfs diff=lfs merge=lfs -text *.bin | .gitattributes content + headers |
| owner-head-gitattributes | HF_OWNER_ACCESS_TOKEN | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 200 |  |  | HEAD headers of a small file |
| owner-head-lfs | HF_OWNER_ACCESS_TOKEN | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/checkpoint-0/model.safetensors` | 302 |  | Location: https://us.aws.cdn.hf.co/xet-bridge-us/6ac4f6932fb5557d4ceee81f/c9a7ab6a87eaa2ed02b787b3c4959e217c1d43b46ab601eb3c735a998774b0dc?<signed-query-redacted> | HEAD of an LFS file (redirect?) |
| owner-config | HF_OWNER_ACCESS_TOKEN | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/checkpoint-0/config.json` | 200 |  | {   "activation_function": "gelu_new",   "add_cross_attention": false,   "architectures":  | a small JSON file in a subfolder |
| anon-readme | anonymous | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/README.md` | 200 |  | --- license: mit ---  # tiny-gated-model  A tiny, randomly initialised GPT-2 (2 layers, 64 | allowlisted anonymously (ACC-5) |
| anon-head-readme | anonymous | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/README.md` | 200 |  |  | HEAD allowlisted |
| anon-ask-access-get | anonymous | `GET /OwnerOfTheGatedModel/tiny-gated-model/ask-access` | 404 |  | Sorry, we can't find the page you are looking for. | GET on the POST-only web route |
| owner-unknown-repo-list | HF_OWNER_ACCESS_TOKEN | `GET /api/models/OwnerOfTheGatedModel/does-not-exist-xyz/user-access-request/pending` | 404 | RepoNotFound | Repository not found | owner list on a missing repo |
| owner-not-gated-list | HF_OWNER_ACCESS_TOKEN | `GET /api/models/openai-community/gpt2/user-access-request/pending` | 403 |  | You have read access but not the required permissions for this operation | list on someone else's non-gated repo |
