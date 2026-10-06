# Hugging Face gated models: replication take-home

A verified clone of Hugging Face's gated-model access requests: the in-memory backend, the screens,
the evidence that it matches the real Hub, and the AI harness that built it.
Write-up: [writeup.md](writeup.md) · Brief: [docs/assignement.md](docs/assignement.md) · Results:
[docs/hf-gated/verification/](docs/hf-gated/verification/README.md)

## Run

Requires [uv](https://docs.astral.sh/uv/) and Node 22. First time only:

```bash
npm --prefix web install
```

Then, in two terminals:

```bash
uv run --project clone clone
```

```bash
npm --prefix web run dev
```

Open http://localhost:3000. The header switches the **persona** (anonymous / owner / requester) and
the **backend**. **Reset clone**, or restarting the clone, brings back the clean seed (no access
request). The clone is in memory only and deterministic.

Optional, the real Hub through the bridge: it needs `HF_OWNER_ACCESS_TOKEN` and
`HF_REQUESTER_ACCESS_TOKEN` in `.env` and only acts on the sandbox repo. Writes reach huggingface.co.

```bash
uv run --project bridge bridge
```

## Tests

```bash
uv run --project clone pytest clone/tests
```

```bash
uv run --project conformance pytest conformance/tests
```

The second one is the blind conformance suite and needs the clone running on :8200.

```bash
npm --prefix web test
```

```bash
npm --prefix web run test:e2e:clone
```

The last one is the scripted UI walkthrough on the clone, diffed against the live recording.

## Structure

| Path | What |
|---|---|
| `clone/` | In-memory, HF-compatible backend (Python, FastAPI): state machine, wire protocol, seeds, `/__clone__/*` controls |
| `bridge/` | Proxy to huggingface.co with personas and safety allowlists (Python) |
| `web/` | The screens (Next.js): gate box, settings, review modal, `/settings/gated-repos` |
| `conformance/` | Blind suite: replays the live recordings, rule tests, official `huggingface_hub` client |
| `docs/` | Knowledge base: method, spec with rule IDs, open questions, recordings, verification |
| `harness/` | AI harness: agent prompts as used, probe and log-diff tools |
| `AGENTS.md` | Instructions for coding agents (also loaded through `CLAUDE.md`) |
