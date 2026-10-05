<!-- Published copy of conformance/reports/latest.md (regenerate with `uv run --project conformance conformance-report --pytest`, clone on :8200). -->
# Conformance report: clone vs real-Hub recordings

Generated 2026-10-05T15:18:30Z against `http://127.0.0.1:8200` by `conformance-report` (conformance/). Ground truth: `docs/hf-gated/observations/2026-10-05-*.json`. Expectations come from the recordings and the KB only (the suite never reads the clone's code). Reproduce with `uv run --project conformance conformance-report --pytest` (clone on :8200).

## Summary

Overall: **PASS** (0 failing scenario(s), 0 stale divergence(s)).

| scenario | recording | steps | pass | diverged (listed) | fail | skipped | error | result |
|---|---|---|---|---|---|---|---|---|
| owner-walkthrough | `2026-10-05-owner-walkthrough.json` | 98 | 98 | 0 | 0 | 0 | 0 | **PASS** |
| owner-walkthrough-completion | `2026-10-05-owner-walkthrough-completion.json` | 44 | 44 | 0 | 0 | 0 | 0 | **PASS** |
| requester-ask-access | `2026-10-05-requester-ask-access.json` | 11 | 10 | 0 | 0 | 1 | 0 | **PASS** |
| owner-reads | `2026-10-05-owner-reads.json` | 8 | 8 | 0 | 0 | 0 | 0 | **PASS** |
| clone-seed-reads (stand-ins) | `2026-10-05-clone-seed-reads.json` | 19 | 18 | 1 | 0 | 0 | 0 | **PASS** |
| ui-walkthrough | `2026-10-05-ui-walkthrough.json` | 62 | 62 | 0 | 0 | 0 | 0 | **PASS** |
| anonymous-probes (stand-ins) | `2026-10-05-anonymous-probes.json` | 44 | 36 | 0 | 0 | 8 | 0 | **PASS** |
| tree-masking | `2026-10-05-tree-masking.json` | 6 | 6 | 0 | 0 | 0 | 0 | **PASS** |

## Unexpected mismatches (verbatim)

None.

## Stale divergences

A listed replay divergence that covers no mismatch in this run fails the run: the known-gaps list must not overstate the gaps.

None.

## Listed divergences (conformance/divergences.yaml)

| id | scenario / step / field | rule | reason | diffs covered |
|---|---|---|---|---|
| D-1 | `clone-seed-reads` / `owner-head-lfs` / `["header:location", "header:link"]` | out-of-scope.md "Real file serving (LFS/Xet, 302 to CDN)" | Out of scope. HF redirects an LFS/Xet file to its CDN (signed URL) and advertises Xet endpoints in Link; the clone serves stub bytes for authorised files and redirects to its own resolve-cache. The authorisation decision (302 for the owner, X-Repo-Commit, X-Linked-Size/-Etag) is still compared and matches. | 2 |
| D-4 | `rules:test_rules_requests` / `test_REV_7_grant_on_non_gated_repo_is_400` / `*` | REV-7 vs open-questions.md "Provisional choices in the clone" (Q-9) | Clone provisional choice. behaviour.md REV-7 says granting on a non-gated repo answers 400 [CLIENT doc]; the clone records "No 'repo not gated' 400 on grant/handle (wording unknown, and CFG-6 shows the lists still work)" and answers 200 {}. Neither side is observed on the Hub. KB inconsistency: REV-7 should carry the Q-9 caveat, or grant on a non-gated repo should be recorded. | pytest strict xfail |

## Scope restrictions

Steps not replayed, or compared on a subset of fields, and why (from `conformance/scenarios.yaml`).

- requester-ask-access / `pre-page`: skipped. HTML model page: rendered by web/, not part of the backend surface (docs/system.md, 'Backend surface')
- anonymous-probes / `page`: skipped. HTML model page (web/), not part of the backend surface (docs/system.md)
- anonymous-probes / `page-tree`: skipped. HTML files page (web/), not part of the backend surface (docs/system.md)
- anonymous-probes / `discussions-page`: skipped. HTML discussions page, not part of the backend surface (docs/system.md)
- anonymous-probes / `discussions-api`: skipped. /api/models/{id}/discussions is not part of the backend surface (docs/system.md); ACC-4 only notes it stays public
- anonymous-probes / `info-revision`: skipped. /api/models/{id}/revision/{rev} is not part of the backend surface (docs/system.md)
- anonymous-probes / `gate-props-auto`: skipped. HTML page props (gate box), checked by the web UI tests, not by the backend
- anonymous-probes / `gate-props-manual-custom`: skipped. HTML page props (gate box), checked by the web UI tests, not by the backend
- anonymous-probes / `gate-props-heading`: skipped. HTML page props (gate box) of google/gemma-2-2b; the Gemma special case is out of scope
- anonymous-probes / `tree`: only `status`, `header:content-type`. stand-in repo: the real Llama-3.2-1B file list (oids, sizes) is not reproducible
- Stand-in repos (`meta-llama/Llama-3.2-1B`, `bigcode/starcoder`, `mistralai/Mistral-7B-v0.1`, `openai-community/gpt2`) are seeded locally with the recorded ids, `_id` and `gated`; their file contents are stubs (the recorded 160-character excerpt), so for them only status, error headers, content type and allowlist decisions carry evidence.

## Normalisations

- **e-mail addresses**: Recordings are redacted (`<email>`, or `<HF_REQUESTER_LOGIN>` whose value is an e-mail). Every e-mail address in the backend's response becomes `<email>` before comparing; presence and position are still checked.
- **timestamps**: Times the backend generates come from its virtual clock, not the Hub's wall clock. Each recorded ISO timestamp is matched to the backend's: timestamps present in the initial seed must come back verbatim; the others must keep the recorded equalities (same recorded value -> same backend value, different -> different) and the recorded order, and use HF's format `YYYY-MM-DDTHH:MM:SS.mmmZ`.
- **ETag of generated responses**: JSON, HTML and error bodies carry a weak ETag that hashes the serialised body; it is ignored. File ETags (responses with Content-Disposition or X-Repo-Commit) are compared, after stripping a `W/` prefix: HF weakens the ETag when it gzips the response, which the bridge's HTTP client asks for and probe.py does not.
- **Content-Length**: Ignored (the bridge drops it; body bytes are compared instead).
- **URL origins**: In `Location`, in `Link` targets and in the `Redirecting to <url>` text of a 3xx body, the origins https://huggingface.co, the bridge (http://127.0.0.1:8100) and the backend under test become `<origin>`. Absolute vs relative is kept. Origins inside messages (for example `Visit https://huggingface.co/{id} to ask for access.`) are NOT normalised.
- **cut recordings**: Where a recording only kept a prefix (probe excerpts of 160 characters, bridge-log strings cut at 2000 characters and marked `…`), the backend's value must start with it. A cut JSON excerpt is compared against the backend's JSON re-serialised compactly (`separators=(',', ':')`, as HF serialises), so whitespace is not compared but key order is.
- **headers not captured**: A header is checked for presence/absence only if the recording could have captured it: those probe.py kept from its first version (X-Error-Code, X-Error-Message, Content-Type, Location, Link, WWW-Authenticate; git 7e14ba3) always; the others (Content-Disposition, ETag, X-Repo-Commit, X-Linked-*) only in recordings where they appear at least once, because probe.py's list grew during the day (07aa65a, 42cc2c8) and the bridge forwards a fixed subset.

## Rule, provisional and client tests (pytest)

pytest exit code 0.

| module | passed | failed | error | xfailed (listed divergence) | skipped |
|---|---|---|---|---|---|
| `tests.test_harness_offline` | 34 | 0 | 0 | 0 | 0 |
| `tests.test_hf_client` | 10 | 0 | 0 | 0 | 0 |
| `tests.test_provisional_clone` | 62 | 0 | 0 | 0 | 0 |
| `tests.test_rules_control` | 11 | 0 | 0 | 0 | 0 |
| `tests.test_rules_errors` | 34 | 0 | 0 | 0 | 0 |
| `tests.test_rules_gate` | 93 | 0 | 0 | 0 | 0 |
| `tests.test_rules_lists` | 14 | 0 | 0 | 0 | 0 |
| `tests.test_rules_outbox` | 7 | 0 | 0 | 0 | 0 |
| `tests.test_rules_report` | 3 | 0 | 0 | 0 | 0 |
| `tests.test_rules_requests` | 27 | 0 | 0 | 1 | 0 |
| `tests.test_scenarios` | 9 | 0 | 0 | 0 | 0 |

Known divergences (strict xfail, see divergences.yaml):

- `tests.test_rules_requests::test_REV_7_grant_on_non_gated_repo_is_400`: D-4 (REV-7 vs open-questions.md "Provisional choices in the clone" (Q-9)): Clone provisional choice. behaviour.md REV-7 says granting on a non-gated repo answers 400 [CLIENT doc]; the clone records "No 'repo not gated' 400 on grant/handle (wording unknown, and CFG-6 shows the lists still work)" and …

## Per-step detail

### owner-walkthrough

Covers: REV-1, REV-2, REV-3, REV-5, REV-7, REV-8, REV-9, REV-10, REV-12, REQ-2, REQ-4, REQ-6, TS-1, TS-2, CFG-3, CFG-6, ACC-7, REP-1, §2 states, Q-2, Q-4, Q-6, Q-7, Q-9, Q-21.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| s0-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s0-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s0-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s0-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s0-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s0-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s1-accept | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s1-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s1-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s1-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s1-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s1-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s1-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s1-accept-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s1-report | owner | `GET /Orosius/deltanet-mla-latent/user-access-report` | 200 → 200 | pass |  |
| s2-cancel | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s2-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s2-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s2-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s2-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s2-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s2-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s2-cancel-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s3-reject | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s3-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s3-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s3-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s3-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s3-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s3-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s3-reject-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s3-req-ask-again | requester | `POST /Orosius/deltanet-mla-latent/ask-access` | 303 → 303 | pass |  |
| s3b-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s3b-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s3b-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s3b-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s3b-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s3b-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s4-accept-from-rejected | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| s4-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s4-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s4-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s4-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s5-reset | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| s5-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s5-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s5-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s5-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s5-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s5-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s5-req-ask-after-reset | requester | `POST /Orosius/deltanet-mla-latent/ask-access` | 303 → 303 | pass |  |
| s5b-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s5b-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s5b-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s5b-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s5b-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s5b-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s6-grant-while-pending | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/grant` | 200 → 200 | pass |  |
| s6-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s6-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s6-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s6-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s6-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 200 → 200 | pass |  |
| s6-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| s6-grant-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/grant` | 400 → 400 | pass |  |
| s7-handle-unknown-user | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| s7-handle-bad-status | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 400 → 400 | pass |  |
| s7-reject-reason-too-long | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 400 → 400 | pass |  |
| s7-handle-no-user | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 400 → 400 | pass |  |
| s7-list-limit-5 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted?limit=5` | 400 → 400 | pass |  |
| s7-list-q | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted?q=testingb` | 200 → 200 | pass |  |
| s7-req-handle | requester | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 403 → 403 | pass |  |
| s8-batch | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/batch` | 200 → 200 | pass |  |
| s8-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s8-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s8-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s8-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s8-batch-same-status | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/batch` | 200 → 200 | pass |  |
| s9-to-auto | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| s9-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s9-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s9-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s9-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s9-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s9-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s9-to-manual | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| s10-to-false | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| s10-list-pending-not-gated | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s10-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 200 → 200 | pass |  |
| s10-anon-resolve | anonymous | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 307 → 307 | pass |  |
| s10-to-manual | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| s10-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| s10-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| s10-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| s10-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| s10-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| s10-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| s11-report | owner | `GET /Orosius/deltanet-mla-latent/user-access-report` | 200 → 200 | pass |  |

### owner-walkthrough-completion

Covers: REV-1, REV-3, REV-5, REQ-4, REQ-6, TS-1, TS-2, §2 states, §5.1 table, Q-2, Q-4, Q-5, Q-8.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| m0-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| m0-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| m0-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| m0-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| m0-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| m0-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| m1-accept | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| m1-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| m1-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| m1-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| m1-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| m1-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 200 → 200 | pass |  |
| m1-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| m2-accept-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| m3-cancel-by-userid | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| m3-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| m3-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| m3-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| m3-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| m3-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| m3-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| m4-cancel-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| m5-reject | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| m5-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| m5-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| m5-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| m5-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| m5-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| m5-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| m6-reject-again | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 404 → 404 | pass |  |
| m7-req-ask-after-reject | requester | `POST /Orosius/deltanet-mla-latent/ask-access` | 303 → 303 | pass |  |
| m7-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| m7-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| m7-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| m7-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| m7-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| m7-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| m8-reset-from-rejected | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| m8-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| m8-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| m8-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| m8-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| m8-req-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| m8-req-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |

### requester-ask-access

Covers: REQ-2, §2 states, REV-12, Q-1, Q-2, Q-8.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| pre-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| pre-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| pre-head | requester | `HEAD /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| pre-owner-list | requester | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 403 → 403 | pass |  |
| pre-page | requester | `GET /Orosius/deltanet-mla-latent` | 200 → — | skipped | HTML model page: rendered by web/, not part of the backend surface (docs/system.md, 'Backend surface') |
| ask-access-json | requester | `POST /Orosius/deltanet-mla-latent/ask-access` | 303 → 303 | pass |  |
| post-json-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| post-json-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |
| ask-access-form | requester | `POST /Orosius/deltanet-mla-latent/ask-access` | 303 → 303 | pass |  |
| post-form-auth-check | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| post-form-resolve | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 403 → 403 | pass |  |

### owner-reads

Covers: REP-1, ACC-1, CFG-3, REQ-6, Q-14.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| owner-list-pending | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| owner-list-accepted | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| owner-list-rejected | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| owner-list-reset | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/reset` | 200 → 200 | pass |  |
| owner-report | owner | `GET /Orosius/deltanet-mla-latent/user-access-report` | 200 → 200 | pass |  |
| owner-auth-check | owner | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 200 → 200 | pass |  |
| owner-get-settings | owner | `GET /api/models/Orosius/deltanet-mla-latent/settings` | 404 → 404 | pass |  |
| owner-resolve | owner | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 → 200 | pass |  |

### clone-seed-reads

Covers: ACC-4, ACC-5, api.md §3.3 check order, system.md Personas (401 wording), system.md seed fidelity.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| model-info-anon | anonymous | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| model-info-owner | owner | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| model-info-expand | anonymous | `GET /api/models/Orosius/deltanet-mla-latent?expand[]=gated&expand[]=cardData` | 200 → 200 | pass |  |
| tree-main | anonymous | `GET /api/models/Orosius/deltanet-mla-latent/tree/main` | 200 → 200 | pass |  |
| tree-subdir | anonymous | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 → 200 | pass |  |
| whoami-owner | owner | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| whoami-requester | requester | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| whoami-anon | anonymous | `GET /api/whoami-v2` | 401 → 401 | pass |  |
| whoami-bad-token | bad | `GET /api/whoami-v2` | 401 → 401 | pass |  |
| owner-readme | owner | `GET /Orosius/deltanet-mla-latent/resolve/main/README.md` | 200 → 200 | pass |  |
| owner-gitattributes | owner | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| owner-head-gitattributes | owner | `HEAD /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| owner-head-lfs | owner | `HEAD /Orosius/deltanet-mla-latent/resolve/main/checkpoint_tokens_20M_loss_4.9842/pytorch_model.bin` | 302 → 302 | diverged | header:link [D-1]; header:location [D-1] |
| owner-config | owner | `GET /Orosius/deltanet-mla-latent/resolve/main/checkpoint_tokens_20M_loss_4.9842/config.json` | 200 → 200 | pass |  |
| anon-readme | anonymous | `GET /Orosius/deltanet-mla-latent/resolve/main/README.md` | 200 → 200 | pass |  |
| anon-head-readme | anonymous | `HEAD /Orosius/deltanet-mla-latent/resolve/main/README.md` | 200 → 200 | pass |  |
| anon-ask-access-get | anonymous | `GET /Orosius/deltanet-mla-latent/ask-access` | 404 → 404 | pass |  |
| owner-unknown-repo-list | owner | `GET /api/models/Orosius/does-not-exist-xyz/user-access-request/pending` | 404 → 404 | pass |  |
| owner-not-gated-list | owner | `GET /api/models/openai-community/gpt2/user-access-request/pending` | 403 → 403 | pass |  |

### ui-walkthrough

Covers: §4 reset -> re-request, §5.1 table, REV-1, REQ-6, TS-1, TS-2, CFG-3, CFG-6, CFG-7, ACC-1, Q-7.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| 191 | requester | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 192 | requester | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 193 | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| 194 | requester | `POST /Orosius/deltanet-mla-latent/ask-access` | 303 → 303 | pass |  |
| 195 | requester | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 196 | requester | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 197 | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| 198 | owner | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 199 | owner | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 200 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 201 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 202 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 203 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 204 | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| 205 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 206 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 207 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 208 | requester | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 209 | requester | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 210 | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 200 → 200 | pass |  |
| 211 | requester | `GET /Orosius/deltanet-mla-latent/resolve/main/.gitattributes` | 200 → 200 | pass |  |
| 212 | owner | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 213 | owner | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 214 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 215 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 216 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 217 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 218 | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| 219 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 220 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 221 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 222 | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| 223 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 224 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 225 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 226 | requester | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 227 | requester | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 228 | requester | `GET /api/models/Orosius/deltanet-mla-latent/auth-check` | 403 → 403 | pass |  |
| 229 | owner | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 230 | owner | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 231 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 232 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 233 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 234 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 235 | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| 236 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 237 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 238 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 239 | owner | `POST /api/models/Orosius/deltanet-mla-latent/user-access-request/handle` | 200 → 200 | pass |  |
| 240 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |
| 241 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/accepted` | 200 → 200 | pass |  |
| 242 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/rejected` | 200 → 200 | pass |  |
| 243 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 244 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 245 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 246 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 247 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 248 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 249 | owner | `PUT /api/models/Orosius/deltanet-mla-latent/settings` | 200 → 200 | pass |  |
| 250 | owner | `GET /api/models/Orosius/deltanet-mla-latent` | 200 → 200 | pass |  |
| 251 | owner | `GET /api/whoami-v2` | 200 → 200 | pass |  |
| 252 | owner | `GET /api/models/Orosius/deltanet-mla-latent/user-access-request/pending` | 200 → 200 | pass |  |

### anonymous-probes

Covers: ACC-3, ACC-4, ACC-5, ACC-6, ACC-10, CFG-5, REP-2, api.md §3.1-3.3.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| meta-manual | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B?expand[]=gated` | 200 → 200 | pass |  |
| meta-auto | anonymous | `GET /api/models/bigcode/starcoder?expand[]=gated` | 200 → 200 | pass |  |
| meta-not-gated | anonymous | `GET /api/models/mistralai/Mistral-7B-v0.1?expand[]=gated` | 200 → 200 | pass |  |
| info-revision | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/revision/main` | 200 → — | skipped | /api/models/{id}/revision/{rev} is not part of the backend surface (docs/system.md) |
| tree | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/tree/main` | 200 → 200 | pass | stand-in repo: the real Llama-3.2-1B file list (oids, sizes) is not reproducible |
| page | anonymous | `GET /meta-llama/Llama-3.2-1B` | 200 → — | skipped | HTML model page (web/), not part of the backend surface (docs/system.md) |
| page-tree | anonymous | `GET /meta-llama/Llama-3.2-1B/tree/main` | 200 → — | skipped | HTML files page (web/), not part of the backend surface (docs/system.md) |
| discussions-page | anonymous | `GET /meta-llama/Llama-3.2-1B/discussions` | 200 → — | skipped | HTML discussions page, not part of the backend surface (docs/system.md) |
| discussions-api | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/discussions` | 200 → — | skipped | /api/models/{id}/discussions is not part of the backend surface (docs/system.md); ACC-4 only notes it stays public |
| resolve-config-manual | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/config.json` | 401 → 401 | pass |  |
| resolve-config-auto | anonymous | `GET /bigcode/starcoder/resolve/main/config.json` | 401 → 401 | pass |  |
| head-config-auto | anonymous | `HEAD /bigcode/starcoder/resolve/main/config.json` | 401 → 401 | pass |  |
| resolve-gitattributes | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/.gitattributes` | 401 → 401 | pass |  |
| resolve-subdir | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/original/params.json` | 401 → 401 | pass |  |
| resolve-use-policy | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/USE_POLICY.md` | 401 → 401 | pass |  |
| allow-readme | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README.md` | 200 → 200 | pass |  |
| allow-readme-auto | anonymous | `GET /bigcode/starcoder/resolve/main/README.md` | 200 → 200 | pass |  |
| allow-license-txt | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE.txt` | 200 → 200 | pass |  |
| allow-license-missing | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE` | 404 → 404 | pass |  |
| allow-license-md-missing | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE.md` | 404 → 404 | pass |  |
| deny-readme-lower | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/readme.md` | 401 → 401 | pass |  |
| deny-readme-upper-ext | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README.MD` | 401 → 401 | pass |  |
| deny-readme-txt | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README.txt` | 401 → 401 | pass |  |
| deny-readme-noext | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README` | 401 → 401 | pass |  |
| deny-license-rst | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE.rst` | 401 → 401 | pass |  |
| deny-license-lower | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/license.txt` | 401 → 401 | pass |  |
| deny-licence | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENCE` | 401 → 401 | pass |  |
| deny-copying | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/COPYING` | 401 → 401 | pass |  |
| deny-subdir-readme | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/original/README.md` | 401 → 401 | pass |  |
| deny-subdir-license | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/original/LICENSE.txt` | 401 → 401 | pass |  |
| raw-readme | anonymous | `GET /meta-llama/Llama-3.2-1B/raw/main/README.md` | 401 → 401 | pass |  |
| blob-config | anonymous | `GET /meta-llama/Llama-3.2-1B/blob/main/config.json` | 401 → 401 | pass |  |
| gate-before-entry | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/does-not-exist.bin` | 401 → 401 | pass |  |
| gate-before-revision | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/nonexistent-branch/config.json` | 401 → 401 | pass |  |
| missing-repo-resolve | anonymous | `GET /someone-xyz123/definitely-not-a-repo/resolve/main/config.json` | 401 → 401 | pass |  |
| auth-check-gated | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/auth-check` | 401 → 401 | pass |  |
| auth-check-public | anonymous | `GET /api/models/openai-community/gpt2/auth-check` | 200 → 200 | pass |  |
| auth-check-missing | anonymous | `GET /api/models/someone-xyz123/definitely-not-a-repo/auth-check` | 401 → 401 | pass |  |
| owner-list-anon | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/user-access-request/pending` | 401 → 401 | pass |  |
| owner-list-not-gated-anon | anonymous | `GET /api/models/openai-community/gpt2/user-access-request/pending` | 401 → 401 | pass |  |
| report-anon | anonymous | `GET /meta-llama/Llama-3.2-1B/user-access-report` | 401 → 401 | pass |  |
| gate-props-auto | anonymous | `GET /bigcode/starcoder` | 200 → — | skipped | HTML page props (gate box), checked by the web UI tests, not by the backend |
| gate-props-manual-custom | anonymous | `GET /meta-llama/Llama-3.2-1B` | 200 → — | skipped | HTML page props (gate box), checked by the web UI tests, not by the backend |
| gate-props-heading | anonymous | `GET /google/gemma-2-2b` | 200 → — | skipped | HTML page props (gate box) of google/gemma-2-2b; the Gemma special case is out of scope |

### tree-masking

Covers: ACC-9, ACC-10, ACC-4.

| step | persona | request | status rec → backend | outcome | notes |
|---|---|---|---|---|---|
| tree-subdir-anon | anonymous | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 → 200 | pass |  |
| tree-subdir-owner | owner | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 → 200 | pass |  |
| tree-subdir-requester | requester | `GET /api/models/Orosius/deltanet-mla-latent/tree/main/checkpoint_tokens_20M_loss_4.9842` | 200 → 200 | pass |  |
| raw-readme-owner | owner | `GET /Orosius/deltanet-mla-latent/raw/main/README.md` | 200 → 200 | pass |  |
| raw-readme-requester | requester | `GET /Orosius/deltanet-mla-latent/raw/main/README.md` | 403 → 403 | pass |  |
| raw-readme-anon | anonymous | `GET /Orosius/deltanet-mla-latent/raw/main/README.md` | 401 → 401 | pass |  |

