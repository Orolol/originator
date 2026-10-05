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
| `harness/kb/` | KB tooling: `probe.py` (scripted probes; read-only unless `--allow-writes`), `extract_openapi.py` (vendor-spec extract), `probes/*.json` (cases) |
| `bridge/` | Python (uv, FastAPI, httpx): HF-compatible proxy with personas, route/repo allowlists, exchange log. See `bridge/README.md` |
| `clone/` (planned) | Python (uv, FastAPI proposed): in-memory HF-compatible backend for the slice |
| `web/` (planned) | Next.js (App Router, TypeScript): requester gate box and owner settings/review screens; talks to `BACKEND_URL` (bridge or clone) |
| `conformance/` (planned) | Scenario scripts run against both backends: API level (pytest + `huggingface_hub`) and UI level (Playwright) |
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

- Sandbox repo: `Orosius/deltanet-mla-latent` (owner `Orosius`, `gated: "manual"`, no extra form
  fields). Requester account: `TestingBOrig`. Its request has been **pending since
  2026-10-05**, which needs an owner action before requester "no request" baselines can be re-recorded.
- `.env` (gitignored) holds `HF_REQUESTER_LOGIN`, `HF_REQUESTER_MDP`, `HF_REQUESTER_ACCESS_TOKEN`. Scripts
  use only the access token (`probe.py --env-file .env` redacts every `.env` value from its output).
  **Never read, print or use `HF_REQUESTER_MDP`**: agents do not type passwords into HF. No owner
  token exists yet (proposed name: `HF_OWNER_ACCESS_TOKEN`), so owner-side endpoints are unverified.
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

KB probes:

```bash
python3 harness/kb/probe.py harness/kb/probes/hf-gated-anonymous.json --out-json docs/hf-gated/observations/<date>-anonymous-probes.json --out-md docs/hf-gated/observations/<date>-anonymous-probes.md
```

```bash
python3 harness/kb/probe.py harness/kb/probes/<cases>.json --env-file .env --allow-writes --out-json docs/hf-gated/observations/<date>-<name>.json --out-md docs/hf-gated/observations/<date>-<name>.md
```

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
| Unknowns and their priority (Q-1…Q-24) | [docs/hf-gated/open-questions.md](docs/hf-gated/open-questions.md) |
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
- No git repository yet (2026-10-05). Once it is initialised, commit at each natural step, per the
  global rules, and stage by path.
