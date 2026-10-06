# Conformance report: clone vs real-Hub recordings

Generated 2026-10-06T18:33:23Z against `http://127.0.0.1:8100` by `conformance-report` (conformance/). Ground truth: the real-Hub recording sets under `docs/hf-gated/observations/`, each replayed from its own initial state: `2026-10-05-*.json` (sandbox `Orosius/deltanet-mla-latent`, owner `Orosius`) and `2026-10-06-*.json` (sandbox `OwnerOfTheGatedModel/tiny-gated-model`, owner `OwnerOfTheGatedModel`); requester `TestingBOrig` in every set. Scenarios are named `<set>/<recording>`. Expectations come from the recordings and the KB only (the suite never reads the clone's code). Reproduce with `uv run --project conformance conformance-report --pytest` (clone on :8200).

## Summary

Overall: **FAIL** (1 failing scenario(s), 0 stale divergence(s)).

| scenario | recording | steps | pass | diverged (listed) | fail | skipped | error | result |
|---|---|---|---|---|---|---|---|---|
| live:2026-10-06/owner-reads | `2026-10-06-owner-reads.json` | 8 | 2 | 0 | 0 | 6 | 0 | **PASS** |
| live:2026-10-06/clone-seed-reads (stand-ins) | `2026-10-06-clone-seed-reads.json` | 19 | 13 | 0 | 2 | 4 | 0 | **FAIL** |
| live:2026-10-06/tree-masking | `2026-10-06-tree-masking.json` | 6 | 4 | 0 | 0 | 2 | 0 | **PASS** |

## Unexpected mismatches (verbatim)

### live:2026-10-06/clone-seed-reads

| step | request | field | expected (recording) | actual (backend) | detail |
|---|---|---|---|---|---|
| whoami-owner | `owner GET /api/whoami-v2` | `body$.auth.accessToken.displayName` | `orig` | `a` |  |
| whoami-owner | `owner GET /api/whoami-v2` | `body$.auth.accessToken.createdAt` | `2026-10-06T13:15:23.159Z` | `2026-10-06T18:32:23.698Z` | order differs from recording relative to 2026-10-06T13:24:38.000Z (backend 2026-10-06T13:24:38.000Z) |
| whoami-requester | `requester GET /api/whoami-v2` | `body$.auth.accessToken.displayName` | `origLap` | `orig` |  |
| whoami-requester | `requester GET /api/whoami-v2` | `body$.auth.accessToken.createdAt` | `2026-10-06T13:21:13.627Z` | `2026-10-05T13:28:04.823Z` | order differs from recording relative to 2026-10-06T13:15:23.159Z (backend 2026-10-06T18:32:23.698Z) |

## Stale divergences

A listed replay divergence that covers no mismatch in this run fails the run: the known-gaps list must not overstate the gaps.

None.

## Listed divergences (conformance/divergences.yaml)

| id | scenario / step / field | rule | reason | diffs covered |
|---|---|---|---|---|
| D-1 | `????-??-??/clone-seed-reads` / `owner-head-lfs` / `["header:location", "header:link"]` | out-of-scope.md "Real file serving (LFS/Xet, 302 to CDN)" | Out of scope. HF redirects an LFS/Xet file to its CDN (signed URL) and advertises Xet endpoints in Link; the clone serves stub bytes for authorised files and redirects to its own resolve-cache. The authorisation decision (302 for the owner, X-Repo-Commit, X-Linked-Size/-Etag) is still compared and matches. Applies to both recording sets (the LFS file is checkpoint_tokens_20M_loss_4.9842/pytorch_mo… | n/a (scenario not run) |
| D-5 | `2026-10-06/edge-cases-a` / `462` / `body$:length` | open-questions.md Q-23 (eventual consistency on the real Hub) | Recording artefact. Right after `handle` pending -> reset (#458), this one reset list came back empty although the requester's auth-check said "has been reset" (#463). The same transition re-probed at 14:44 (2026-10-06-reset-from-pending r1, r1b) lists the entry 1 s and 6 s later, and the report has it: the empty list was the Hub lagging, not a rule. The clone lists the entry. | n/a (scenario not run) |

## Scope restrictions

Steps not replayed, or compared on a subset of fields, and why (from `conformance/scenarios.yaml`).

- 2026-10-05/requester-ask-access / `pre-page`: skipped. HTML model page: rendered by web/, not part of the backend surface (docs/system.md, 'Backend surface')
- 2026-10-05/anonymous-probes / `page`: skipped. HTML model page (web/), not part of the backend surface (docs/system.md)
- 2026-10-05/anonymous-probes / `page-tree`: skipped. HTML files page (web/), not part of the backend surface (docs/system.md)
- 2026-10-05/anonymous-probes / `discussions-page`: skipped. HTML discussions page, not part of the backend surface (docs/system.md)
- 2026-10-05/anonymous-probes / `discussions-api`: skipped. /api/models/{id}/discussions is not part of the backend surface (docs/system.md); ACC-4 only notes it stays public
- 2026-10-05/anonymous-probes / `info-revision`: skipped. /api/models/{id}/revision/{rev} is not part of the backend surface (docs/system.md)
- 2026-10-05/anonymous-probes / `gate-props-auto`: skipped. HTML page props (gate box), checked by the web UI tests, not by the backend
- 2026-10-05/anonymous-probes / `gate-props-manual-custom`: skipped. HTML page props (gate box), checked by the web UI tests, not by the backend
- 2026-10-05/anonymous-probes / `gate-props-heading`: skipped. HTML page props (gate box) of google/gemma-2-2b; the Gemma special case is out of scope
- 2026-10-05/anonymous-probes / `tree`: only `status`, `header:content-type`. stand-in repo: the real Llama-3.2-1B file list (oids, sizes) is not reproducible
- 2026-10-06/requester-ask-access / `pre-page`: skipped. HTML model page: rendered by web/, not part of the backend surface (docs/system.md, 'Backend surface')
- 2026-10-06/edge-cases-a / `528`: only `status`, `header:*`. HF's HTML error page body; the clone answers HTML routes with the message only (docs/system.md)
- Stand-in repos (`meta-llama/Llama-3.2-1B`, `bigcode/starcoder`, `mistralai/Mistral-7B-v0.1`, `openai-community/gpt2`) are seeded locally with the recorded ids, `_id` and `gated`; their file contents are stubs (the recorded 160-character excerpt), so for them only status, error headers, content type and allowlist decisions carry evidence.

## Normalisations

- **e-mail addresses**: Recordings are redacted (`<email>`, or `<HF_REQUESTER_LOGIN>` whose value is an e-mail). Every e-mail address in the backend's response becomes `<email>` before comparing; presence and position are still checked.
- **timestamps**: Times the backend generates come from its virtual clock, not the Hub's wall clock. Each recorded ISO timestamp is matched to the backend's: timestamps present in the initial seed must come back verbatim; the others must keep the recorded equalities (same recorded value -> same backend value, different -> different) and the recorded order, and use HF's format `YYYY-MM-DDTHH:MM:SS.mmmZ`.
- **ETag of generated responses**: JSON, HTML and error bodies carry a weak ETag that hashes the serialised body; it is ignored. File ETags (responses with Content-Disposition or X-Repo-Commit) are compared, after stripping a `W/` prefix: HF weakens the ETag when it gzips the response, which the bridge's HTTP client asks for and probe.py does not.
- **Content-Length**: Ignored (the bridge drops it; body bytes are compared instead).
- **URL origins**: In `Location`, in `Link` targets and in the `Redirecting to <url>` text of a 3xx body, the origins https://huggingface.co, the bridge (http://127.0.0.1:8100) and the backend under test become `<origin>`. Absolute vs relative is kept. Origins inside messages (for example `Visit https://huggingface.co/{id} to ask for access.`) are NOT normalised.
- **cut recordings**: Where a recording only kept a prefix (probe excerpts of 160 characters, bridge-log strings cut at 2000 characters and marked `…`), the backend's value must start with it. A cut JSON excerpt is compared against the backend's JSON re-serialised compactly (`separators=(',', ':')`, as HF serialises), so whitespace is not compared but key order is.
- **headers not captured**: A header is checked for presence/absence only if the recording could have captured it: those probe.py kept from its first version (X-Error-Code, X-Error-Message, Content-Type, Location, Link, WWW-Authenticate; git 7e14ba3) always; the others (Content-Disposition, ETag, X-Repo-Commit, X-Linked-*) only in recordings where they appear at least once, because probe.py's list grew during the day (07aa65a, 42cc2c8) and the bridge forwards a fixed subset.

## Per-step detail

### live:2026-10-06/owner-reads

Covers: REP-1, ACC-1, CFG-3, REQ-6, Q-14.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| owner-list-pending | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/pending` | 200 → — | skipped | not in the live read-only selection |
| owner-list-accepted | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/accepted` | 200 → — | skipped | not in the live read-only selection |
| owner-list-rejected | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/rejected` | 200 → — | skipped | not in the live read-only selection |
| owner-list-reset | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/user-access-request/reset` | 200 → — | skipped | not in the live read-only selection |
| owner-report | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/user-access-report` | 200 → — | skipped | not in the live read-only selection |
| owner-auth-check | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/auth-check` | 200 → 200 | pass |  |
| owner-get-settings | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/settings` | 404 → — | skipped | not in the live read-only selection |
| owner-resolve | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 200 → 200 | pass |  |

### live:2026-10-06/clone-seed-reads

Covers: ACC-4, ACC-5, api.md §3.3 check order, system.md Personas (401 wording), system.md seed fidelity.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| model-info-anon | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` | 200 → 200 | pass |  |
| model-info-owner | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model` | 200 → 200 | pass |  |
| model-info-expand | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model?expand[]=gated&expand[]=cardData` | 200 → 200 | pass |  |
| tree-main | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main` | 200 → 200 | pass |  |
| tree-subdir | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 → 200 | pass |  |
| whoami-owner | owner | `GET /api/whoami-v2` | 200 → 200 | fail | body$.auth.accessToken.displayName; body$.auth.accessToken.createdAt |
| whoami-requester | requester | `GET /api/whoami-v2` | 200 → 200 | fail | body$.auth.accessToken.displayName; body$.auth.accessToken.createdAt |
| whoami-anon | anonymous | `GET /api/whoami-v2` | 401 → 401 | pass |  |
| whoami-bad-token | bad | `GET /api/whoami-v2` | 401 → 401 | pass |  |
| owner-readme | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/README.md` | 200 → 200 | pass |  |
| owner-gitattributes | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| owner-head-gitattributes | owner | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| owner-head-lfs | owner | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/checkpoint-0/model.safetensors` | 302 → — | skipped | not in the live read-only selection |
| owner-config | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/checkpoint-0/config.json` | 200 → 200 | pass |  |
| anon-readme | anonymous | `GET /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/README.md` | 200 → 200 | pass |  |
| anon-head-readme | anonymous | `HEAD /OwnerOfTheGatedModel/tiny-gated-model/resolve/main/README.md` | 200 → 200 | pass |  |
| anon-ask-access-get | anonymous | `GET /OwnerOfTheGatedModel/tiny-gated-model/ask-access` | 404 → — | skipped | not in the live read-only selection |
| owner-unknown-repo-list | owner | `GET /api/models/OwnerOfTheGatedModel/does-not-exist-xyz/user-access-request/pending` | 404 → — | skipped | not in the live read-only selection |
| owner-not-gated-list | owner | `GET /api/models/openai-community/gpt2/user-access-request/pending` | 403 → — | skipped | not in the live read-only selection |

### live:2026-10-06/tree-masking

Covers: ACC-9, ACC-10, ACC-4.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| tree-subdir-anon | anonymous | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 → 200 | pass |  |
| tree-subdir-owner | owner | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 → 200 | pass |  |
| tree-subdir-requester | requester | `GET /api/models/OwnerOfTheGatedModel/tiny-gated-model/tree/main/checkpoint-0` | 200 → — | skipped | not in the live read-only selection |
| raw-readme-owner | owner | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 200 → 200 | pass |  |
| raw-readme-requester | requester | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 403 → — | skipped | not in the live read-only selection |
| raw-readme-anon | anonymous | `GET /OwnerOfTheGatedModel/tiny-gated-model/raw/main/README.md` | 401 → 401 | pass |  |

