# Run: conformance suite re-synced to a second recorded sandbox (2026-10-06)

- Agent type: general-purpose subagent, model **Opus** (verification harness; must judge initial
  states and normalisations from recordings), background, in parallel with the orchestrator's clone,
  web and docs changes.
- Why: the live sandbox moved to a dedicated owner account. Every recording was re-made on
  2026-10-06 on `OwnerOfTheGatedModel/tiny-gated-model`, plus a new requester self-cancel probe (REQ-7)
  and a scripted UI walkthrough driven through the bridge.

## Prompt (verbatim)

You are updating the **blind conformance suite** in `/home/gmartin/worspace/originator/conformance/` (a replica of Hugging Face's gated-models access-request backend is under test). A second set of real-Hub recordings now exists, made on 2026-10-06 on a new sandbox repo with a different owner account. The suite must replay **both** recording sets, each from its own initial state, and its rule tests must target the new sandbox.

## Read first, in order
1. `AGENTS.md` (hard rules: no invented behaviour, never weaken a test, a known gap goes to `conformance/divergences.yaml` with its rule ID and evidence).
2. `docs/system.md` (personas, seed format, `/__clone__/*` control endpoints).
3. `docs/hf-gated/behaviour.md` (rule IDs; note the new **REQ-7** requester self-cancel and the updated **REP-1** report key order) and `docs/hf-gated/open-questions.md`.
4. `conformance/README.md` if present, `conformance/scenarios.yaml`, `conformance/divergences.yaml`, and `conformance/src/conformance/*.py`, `conformance/tests/*.py`.
5. The recordings in `docs/hf-gated/observations/`: the existing `2026-10-05-*` set (sandbox `Orosius/deltanet-mla-latent`, owner `Orosius`) and the new `2026-10-06-*` set (sandbox `OwnerOfTheGatedModel/tiny-gated-model`, owner `OwnerOfTheGatedModel`, requester `TestingBOrig` as before): `clone-seed-reads`, `requester-ask-access`, `owner-reads`, `tree-masking`, `owner-walkthrough`, `owner-walkthrough-completion`, **`requester-cancel`** (new), **`ui-walkthrough`** (bridge-log format, recorded by the scripted Playwright journey `web/e2e/walkthrough.ts`, which starts with TestingBOrig's request in `reset`). There is no new `anonymous-probes`: those probes never touched the sandbox. The `.md` next to each JSON is a readable table. Each JSON `_meta` has `vars` (the placeholder values used) and, for some, a `postprocess` note: read it.

You may NOT read anything under `clone/` except `clone/README.md` and `clone/pyproject.toml`. Expectations come from the recordings and the KB only, never from the clone's code.

## What to do
- Make the seed builders (`seeds.py`, `rule_seeds.py`) work per **recording set** (date / sandbox / owner / owner placeholder e-mail), derived programmatically from that set's `clone-seed-reads` as today — no hand-typed oids. The new sandbox's LFS file is `checkpoint-0/model.safetensors`.
- Keep every `2026-10-05` scenario (renamed if you need a set prefix, e.g. `2026-10-05/owner-walkthrough`; keep names readable in the report) and add the `2026-10-06` ones, including `requester-cancel` and the new `ui-walkthrough`. Write each initial state from what the recording's first steps show (and the previous recording in time order — use `sent_at`), with a comment citing the step ids, exactly like the existing `scenario_seed` entries. Time order on 2026-10-06: clone-seed-reads (no request) → requester-ask-access → owner-reads → tree-masking → owner-walkthrough → owner-walkthrough-completion → requester-cancel → (the live spec then put the request back in `reset` and cleared the log) → ui-walkthrough.
- Update `covers:` with rule IDs (REQ-7 for requester-cancel and the UI walkthrough; REP-1 where a report is replayed).
- Rule tests (`tests/test_rules_*.py`, `test_hf_client.py`, `test_provisional_clone.py`): target the new sandbox and its users (from the 2026-10-06 recordings). Add rule tests for **REQ-7** (pending → deleted, `200 {"ok":true}`; accepted / rejected / reset / none → `404` "No pending access request found for this repo and this user", no `X-Error-Code`, unchanged; anonymous → 401) and for the **REP-1** accepted-entry key order with `grantedBy {fullname, user}`. Name them by rule ID.
- Live mode (`live:` in `scenarios.yaml`, `tests/test_live.py`): read-only steps of the **2026-10-06** set only (the bridge's repo allowlist now only allows the new sandbox).
- Check the existing `divergences.yaml` entries still apply (the stale-divergence check fails otherwise); a divergence that is specific to one set must say which. Do not add a divergence unless it traces to the KB.
- The report header (`report.py`) must list both recording sets.

## How to run
Start your own clone: `CLONE_PORT=8202 uv run --project clone clone` (background), then `BACKEND_URL=http://127.0.0.1:8202 uv run --project conformance pytest conformance/tests` and `BACKEND_URL=http://127.0.0.1:8202 uv run --project conformance conformance-report --pytest`. Stop the clone at the end. Do NOT use ports 8100 (bridge → live Hub), 8200, 8201, 3000–3102. Do not run live mode.

If a replay mismatch looks like a real clone bug (the recording and the KB agree, the clone does not), do NOT bend the expectation: report it verbatim (scenario, step, field, expected, got). The orchestrator decides.

## Constraints
- Only modify `conformance/` (including `scenarios.yaml`, `divergences.yaml`, `reports/`). Do not touch `clone/`, `web/`, `bridge/`, `docs/`, `harness/`, `AGENTS.md`, `writeup.md`. No `git add`/`commit`. Never read `.env`. Never send anything to huggingface.co or the bridge.

## Final report (short)
Commands; test counts (passed / xfailed / failed); the report summary table; every unexpected mismatch verbatim with your diagnosis (clone bug vs recording artefact); divergences added/removed/changed and why.
