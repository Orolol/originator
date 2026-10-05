# Sources (pinned)

Everything in this knowledge base comes from the sources below. Re-check them when they move. To
refresh a pin, re-clone, diff the gated-related files, and update the docs and this file.

| Tag | Source | Pin | Gated-relevant parts |
|---|---|---|---|
| [DOC] | `github.com/huggingface/hub-docs` (source of `huggingface.co/docs/hub`) | `08175d0`, 2026-10-04 | `docs/hub/models-gated.md`, `datasets-gated.md`, `enterprise-gating-group-collections.md`, `collections.md` §Gating Group, `organizations.md`, `security-tokens.md`, `oauth.md` (`gated-repos` scope), `trusted-publishers.md`, `datasetcard.md` (template with `extra_gated_*`), `api.md` (points to the OpenAPI spec) |
| [SPEC] | `https://huggingface.co/.well-known/openapi.json` (OpenAPI 3.1, "Hub API Endpoints"); playground `huggingface.co/spaces/huggingface/openapi`; Markdown `…/.well-known/openapi.md` | fetched 2026-10-05; subset in `snapshots/openapi-gated.json` | settings, `user-access-request/{status,handle,grant,batch,cancel}`, `ask-access`, `user-access-report`, `/api/settings/notifications`, collections `gating` |
| [CLIENT] | `github.com/huggingface/huggingface_hub` | `d699913`, 2026-10-05 | `src/huggingface_hub/hf_api.py` (`AccessRequest`, `update_repo_settings`, `*_access_request`, `grant_access`, `auth_check`), `errors.py` (`GatedRepoError`), `utils/_http.py` (`hf_raise_for_status`), `utils/_pagination.py`, `cli/_errors.py`, `cli/repos.py`, `tests/test_hf_api.py::TestAccessRequestAPI`, `tests/test_file_download.py` |
| [JS] | `github.com/huggingface/huggingface.js` | `3064743`, 2026-10-04 | `packages/hub/src/types/api/api-model.ts` (card-metadata typing incl. `ip_location`), `api-collection.ts` |
| [OBS] | Live `huggingface.co`, anonymous, read-only | 2026-10-05 | `observations/2026-10-05-anonymous-probes.{md,json}`, produced by `harness/kb/probe.py` with `harness/kb/probes/hf-gated-anonymous.json` |
| [OBS] | Live `huggingface.co`, requester account `TestingBOrig` (token) on sandbox repo `Orosius/deltanet-mla-latent` (manual, no extra fields); includes 2 `ask-access` POSTs authorised by the user | 2026-10-05 | `observations/2026-10-05-requester-ask-access.{md,json}`, from `harness/kb/probes/hf-gated-requester-ask-access.json` (`--env-file .env --allow-writes`). Not re-runnable as-is: the requester is now `pending`. |
| [DOC-IMG] | Doc screenshots in `huggingface.co/datasets/huggingface/documentation-images` (`hub/models-gated-*.png`) | viewed 2026-10-05; undated, possibly older than the live UI | see [ui.md](ui.md) |
| [OBS-3P] | Error strings quoted by users in public GitHub issues | searched 2026-10-05 | e.g. `prov-gigapath/prov-gigapath#92` (pending message), `rh-ai-quickstart/ai-virtual-agent#200` (not-authorized message), `meta-llama/llama#1168` (rejected message), `ibrahimethemhamamci/CT-CLIP#32` (dataset variant) |

## Re-fetching

```bash
git clone --depth 1 https://github.com/huggingface/hub-docs
```

```bash
git clone --depth 1 https://github.com/huggingface/huggingface_hub
```

```bash
python3 harness/kb/extract_openapi.py --spec-url https://huggingface.co/.well-known/openapi.json --include 'user-access-request|ask-access|user-access-report|/settings$' --exclude '^/api/(datasets|spaces|buckets|containers|organizations)/|^/datasets/|resource-groups|settings/tokens' --out docs/hf-gated/snapshots/openapi-gated.json
```

```bash
python3 harness/kb/probe.py harness/kb/probes/hf-gated-anonymous.json --out-json docs/hf-gated/observations/<date>-anonymous-probes.json --out-md docs/hf-gated/observations/<date>-anonymous-probes.md
```

Clone into a scratch directory, not into this repo.
