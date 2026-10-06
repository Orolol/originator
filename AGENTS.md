# AGENTS.md: Originator take-home (clone of Hugging Face gated models)

Guide for every coding agent working in this repo (Claude Code loads it through `CLAUDE.md`).
Global machine rules (`~/AGENTS.md`) still apply; this file wins where they overlap.

## What this repo is

- A take-home for Originator (Replication Engineer). Brief: [docs/assignement.md](docs/assignement.md).
  Candidate's write-up: [writeup.md](writeup.md).
- Goal: replicate **one slice of business logic** of a closed-source product. That means a resettable,
  deterministic clone behind a thin API, the screens that exercise it, a test suite proving
  fidelity against the real product, and the AI harness that produced it, all checked in.
- Grading is on **method, verification, honest gaps and AI leverage**, not polish. A small slice
  that is rigorously verified beats a broad one that is only plausible. The time box is about one day of effort.
- Target and slice: **Hugging Face Hub, gated models** (the access-request lifecycle and the file
  authorisation decision it drives). Chosen approach: **bridge into clone** (see `writeup.md`).
  Build the UI against a bridge to the real Hub, then swap in the clone, using the same scripts on both.

## Hard rules

1. **Never edit `writeup.md`.** It is the candidate's own text. Do not edit `docs/assignement.md`
   (the brief) either.
2. **Clone state is in memory only.** No database, no disk-backed store. A process restart or the
   reset call brings back the seeded state.
3. **No invented behaviour.** Everything the clone does traces to a rule in
   [docs/hf-gated/behaviour.md](docs/hf-gated/behaviour.md) (cite the rule ID in code comments
   and tests), or to a provisional choice recorded in
   [docs/hf-gated/open-questions.md](docs/hf-gated/open-questions.md). Model memory about
   HF is not evidence.
4. **Live Hub: read-only, except through the bridge on our sandbox.** Anonymous `GET`/`HEAD`
   probes go through `harness/kb/probe.py`. State-changing calls only go through the bridge, only on
   the sandbox repo(s) owned by the accounts configured in `.env`. Never act on someone else's repo.
   Remember the side effects: each request in manual mode emails the owner, and `reset` emails the user.
5. **Secrets.** HF tokens live only in `.env` (gitignored), never in code, fixtures, logs or
   docs. Redact tokens and personal emails from recordings before committing them.
6. **Do not use HF's CI staging credentials** that appear in `huggingface_hub/tests` (hub-ci is
   HF's infrastructure, not ours).
7. **Behaviour, not pixels.** Copy controls, states, messages and requests fired. No styling work
   beyond what makes the structure readable.
8. **Never weaken a test to make it pass.** A known divergence goes into the divergence list with
   its rule ID and evidence.

## Stack and layout

Python for the clone and the bridge, Next.js for the front end. Rows marked (planned) do not
exist yet. Update this section when they land.

| Path | What |
|---|---|
| `docs/` | Knowledge base. Start at [docs/README.md](docs/README.md) |
| `docs/method.md` | Target-agnostic replication method (the reusable part of the harness) |
| `docs/hf-gated/` | Target KB: spec, wire protocol, UI, open questions, sources, observations |
| `harness/kb/` | KB tooling: `probe.py` (scripted probes; read-only unless `--allow-writes`), `extract_openapi.py` (vendor-spec extract), `bridge_log_to_md.py` (export a bridge/clone log), `compare_logs.py` (diff two logs: ordered writes, multiset of reads), `probes/*.json` (cases) |
| `bridge/` | Python (uv, FastAPI, httpx): HF-compatible proxy with personas, route/repo allowlists, exchange log. See `bridge/README.md` |
| `clone/` | Python (uv, FastAPI): in-memory, deterministic HF-compatible backend (domain state machine, wire protocol, seeds, `/__clone__/*` control endpoints). See `clone/README.md` |
| `web/` | Next.js 16 (App Router, TypeScript): requester gate box, owner settings section, review modal; proxies HF-shaped requests to the backend chosen in its header (clone by default, or bridge; `BACKEND_URL` pins one) (bridge or clone). See `web/README.md`; `web/AGENTS.md` is Next's own agent note |
| `conformance/` | Blind conformance suite: replays the live recordings against a backend, rule tests by ID, the official `huggingface_hub` client, `divergences.yaml` (every accepted gap with its rule/Q id) |
| `docs/hf-gated/verification/` | Published verification results (conformance report, clone-vs-live UI walkthrough diff) |
| `harness/agents/` | Subagent prompts actually used, verbatim, with the shared patterns |
| `harness/` (planned additions) | recorders, diff tooling |

### Design decisions (from the KB)

- **The clone speaks HF's wire protocol**: same paths, JSON shapes, status codes and
  `X-Error-Code` / `X-Error-Message` headers ([docs/hf-gated/api.md](docs/hf-gated/api.md)). The
  official `huggingface_hub` client must work unchanged against it. Gotcha: set `HF_ENDPOINT` *before
  importing* `huggingface_hub`, because the access-request methods ignore `HfApi(endpoint=…)`.
- **Identity**: HF authenticates with Bearer tokens, one per user. The clone seeds users with fixed
  tokens. The web app has an "acting as" switcher (anonymous / owner / requester…). In bridge mode it
  maps to the real tokens from `.env`. The requester side works through the API: `ask-access` accepts a
  Bearer token (Q-1, observed 2026-10-05). HF's HTML pages ignore tokens, though, so real
  logged-in *screens* can only be captured in a browser where the user logged in themselves.
- **Clone-only control endpoints** live under a reserved prefix (`/__clone__/…`: reset, seed,
  clock, outbox) that cannot collide with HF paths.
- **Determinism**: injectable clock, sequential 24-hex ObjectIds, stable list ordering, and an outbox for
  emails.

### Live sandbox (real Hub)

- Sandbox repo (since 2026-10-06): `OwnerOfTheGatedModel/tiny-gated-model` (dedicated owner account
  `OwnerOfTheGatedModel`, `gated: "manual"`, no extra form fields). It holds a tiny, randomly
  initialised GPT-2 (`README.md`, `checkpoint-0/{config.json,generation_config.json,model.safetensors}`).
  Requester account: `TestingBOrig`. After the logged-in browser sessions (2026-10-06 ~19:25Z) its
  request is **rejected** (no reason) and the repo `manual`, notifications `bulk`. The read-only e2e
  (`test:e2e`) expects a pending request, so its owner/requester checks fail until the owner moves
  the request back to pending (rejected tab → Cancel). Always read the current state
  (owner lists) before scripting transitions; the live walkthrough spec does it and resets the request
  itself.
- Previous sandbox: `Orosius/deltanet-mla-latent`, owned by the candidate's personal account (the
  2026-10-05 recordings). It is no longer driven through the bridge; the conformance suite still replays
  its recordings, with seeds built from them. Everything else (clone seeds, e2e, rule tests) uses the
  new sandbox and the 2026-10-06 recordings. At the end of the 2026-10-05 walkthrough (14:23Z)
  its request was back to **pending**; that day a pending request was also cancelled by hand on
  huggingface.co, outside the bridge.
- `.env` (gitignored) holds `HF_OWNER_ACCESS_TOKEN`, `HF_REQUESTER_ACCESS_TOKEN`, `HF_REQUESTER_LOGIN`.
  Scripts use only the tokens (`probe.py --env-file …` redacts every value of that file from its output).
  Give `probe.py` an env file **without** `HF_REQUESTER_LOGIN`: it is now the plain username, so it
  would be redacted wherever it appears (it happened once on 2026-10-06; see `sources.md`).
  Agents never type passwords into HF. Through the bridge, use the fake persona tokens
  (`harness/kb/probes/personas.env`), never the real ones.
- Recorded walkthroughs: `docs/hf-gated/observations/<date>-owner-walkthrough*.md` (API),
  `…-requester-cancel.md` (REQ-7) and `…-ui-walkthrough.md` (bridge log of the UI; on 2026-10-06 the
  scripted journey `web/e2e/walkthrough.ts`). Export a bridge log with `harness/kb/bridge_log_to_md.py`.
- Each `ask-access` on a manual repo may email the owner. Only send state-changing calls the user asked for.

## Commands

Add each command here as soon as it exists (fish-compatible, one per block). Run from the repo root.

Bridge (port 8100; needs `.env` tokens):

```bash
uv run --project bridge bridge
```

```bash
uv run --project bridge pytest bridge/tests
```

```bash
uv run --project bridge pytest bridge/tests -m live
```

The last one is GET/HEAD only, against the real Hub.

Clone (port 8200; in-memory, reset with `POST /__clone__/reset`):

```bash
uv run --project clone clone
```

```bash
uv run --project clone pytest clone/tests
```

Web (port 3000). Start the clone and/or the bridge first. The header switches between them: the clone
is the default, and the bridge writes to the real Hub. A "Reset clone" button restores the clone's
seed. `BACKEND_URL` pins one and disables the switch:

```bash
npm --prefix web run dev
```

```bash
npm --prefix web test
```

```bash
npm --prefix web run test:e2e
```

The e2e suite is read-only against the live bridge: a guard aborts any non-GET/HEAD request.

```bash
npm --prefix web run test:e2e:clone
```

This is the scripted UI walkthrough (`web/e2e/walkthrough.ts`) on web + clone (it starts the clone on
8201 and a production web build on 3101). It diffs the clone's request log against the live run of
the same script, `docs/hf-gated/observations/2026-10-06-ui-walkthrough.json`, with
`harness/kb/compare_logs.py`. The output goes to `web/e2e/out/` (gitignored).

```bash
E2E_LIVE_WRITES=1 npm --prefix web run test:e2e:live
```

The same journey against the real Hub through the bridge (bridge on 8100 first; web on 3102). It
**writes** on the sandbox (ask-access, self-cancel, handle, settings; the owner gets e-mails) and
re-records `docs/hf-gated/observations/<today>-ui-walkthrough.{json,md}`. Only when the user asks.
Without system Chrome, add `PLAYWRIGHT_CHANNEL=chromium` to any e2e command.

Conformance (blind suite; start the clone on 8200 first):

```bash
uv run --project conformance pytest conformance/tests
```

```bash
uv run --project conformance conformance-report --pytest
```

The second command writes `conformance/reports/latest.{md,json}`. Live mode (bridge running, GET/HEAD
only): `BACKEND_URL=http://127.0.0.1:8100 uv run --project conformance conformance-report --live`.
`.claude/launch.json` defines `bridge` (8100), `clone` (8200) and `web` (3000; the backend is chosen in
the UI).

KB probes:

```bash
python3 harness/kb/probe.py harness/kb/probes/hf-gated-anonymous.json --out-json docs/hf-gated/observations/<date>-anonymous-probes.json --out-md docs/hf-gated/observations/<date>-anonymous-probes.md
```

```bash
python3 harness/kb/probe.py harness/kb/probes/<cases>.json --env-file <tokens.env> --var SANDBOX=OwnerOfTheGatedModel/tiny-gated-model --var OWNER=OwnerOfTheGatedModel --var SUBDIR=checkpoint-0 --var LFS_FILE=checkpoint-0/model.safetensors --allow-writes --out-json docs/hf-gated/observations/<date>-<name>.json --out-md docs/hf-gated/observations/<date>-<name>.md
```

Cases use `{SANDBOX}`-style placeholders; `<tokens.env>` holds `HF_OWNER_ACCESS_TOKEN`,
`HF_REQUESTER_ACCESS_TOKEN` (direct cases), the persona tokens of `harness/kb/probes/personas.env`
(`OWNER`, `REQUESTER`: cases through the bridge) and any `BAD_TOKEN`.

```bash
python3 harness/kb/extract_openapi.py --spec-url https://huggingface.co/.well-known/openapi.json --include 'user-access-request|ask-access|user-access-report|/settings$' --exclude '^/api/(datasets|spaces|buckets|containers|organizations)/|^/datasets/|resource-groups|settings/tokens' --out docs/hf-gated/snapshots/openapi-gated.json
```

## Knowledge base: read before touching code

| Need | File |
|---|---|
| What the slice is, glossary, scope | [docs/hf-gated/README.md](docs/hf-gated/README.md) |
| The rules to implement (IDs `CFG/ACC/REQ/REV/TS/REP-*`) | [docs/hf-gated/behaviour.md](docs/hf-gated/behaviour.md) |
| Endpoints, payloads, error headers, client gotchas | [docs/hf-gated/api.md](docs/hf-gated/api.md) |
| Screens, states, side-effect matrix, recording checklist | [docs/hf-gated/ui.md](docs/hf-gated/ui.md) |
| Gate form metadata, seed-worthy live examples | [docs/hf-gated/gate-form.md](docs/hf-gated/gate-form.md) |
| Unknowns and their priority (Q-1…Q-25, plus provisional UI choices) | [docs/hf-gated/open-questions.md](docs/hf-gated/open-questions.md) |
| What `huggingface_hub` covers and its tests as evidence | [docs/hf-gated/client-library.md](docs/hf-gated/client-library.md) |
| Deliberately excluded features | [docs/hf-gated/out-of-scope.md](docs/hf-gated/out-of-scope.md) |
| Evidence tags and their ranking | [docs/README.md](docs/README.md) |

KB maintenance: a new finding updates the rule, carries a tag (`[OBS]` with date and fixture path
when observed by us), and closes or adds the matching `Q-n` in the same change. Generated files
(`observations/`, `snapshots/`) are regenerated, never hand-edited.

## Working method (summary of [docs/method.md](docs/method.md))

Scope → gather tagged evidence → specify rules + questions → record against the real Hub (P0
questions first) → build the clone → run the same scenarios on bridge and clone → fix, or document
the divergence. When you delegate: the **verifier writes scenarios from the spec without reading the
clone's code**, and the implementer never adds behaviour that has no rule.

## Tests

- **Fast (default)**: clone domain logic and clone-level conformance scenarios. No network,
  deterministic, seconds.
- **Live (opt-in)**: the same scenarios through the bridge against huggingface.co. Mark them
  (`@pytest.mark.live`); they need `.env` and the sandbox repo, and tolerate the Hub's eventual
  consistency (Q-23). Never part of the default run.
- Name or parametrise tests by rule ID (for example `test_ACC_5_allowlist[...]`) so coverage per rule is
  visible.

## Language and git

- Code, docs and commits in **English**. The user may chat in French or English.
- Git repository on `main`. Commit at each natural step, per the global rules, and stage by path.
  Subagents do not commit; the orchestrator reviews and commits.
