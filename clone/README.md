# clone

In-memory, deterministic reimplementation of Hugging Face's gated-models access-request backend. It
speaks the same wire protocol as huggingface.co for the slice (paths, payloads, status codes,
`X-Error-*` headers), so the web app, the conformance suite and the official `huggingface_hub`
client run against it unchanged. The contract is in [../docs/system.md](../docs/system.md) ("Clone");
the rules are in [../docs/hf-gated/behaviour.md](../docs/hf-gated/behaviour.md).

## Run

```bash
uv run --project clone clone
```

It listens on `127.0.0.1:8200`. `CLONE_HOST`/`CLONE_PORT` override this; `CLONE_PUBLIC_URL` (default:
host and port) builds absolute URLs such as the `ask-access` `Location`.

```bash
uv run --project clone pytest clone/tests
```

The tests are offline (about 2 s).

```bash
uv run --project clone python clone/scripts/derive_seed.py
```

This regenerates `src/clone/seeds/sandbox.json` from the recorded fixtures; a test checks the
committed seed is up to date.

## State and determinism

- All state is in memory. A restart, `POST /__clone__/reset`, or `PUT /__clone__/state` brings it back
  to a known seed. Nothing is written to disk.
- The virtual clock advances by `tick_ms` per state-changing request, IDs come from a counter, and
  ordering is stable. Same seed + same requests ⇒ byte-identical responses, log and outbox.
- Control endpoints, under `/__clone__/`: `health`, `reset`, `state` (GET/PUT, seed format),
  `clock`, `outbox`, and `log` (same schema as the bridge's log).
- Built-in seed `sandbox`:
  - the real `Orosius/deltanet-mla-latent` as recorded on 2026-10-05, with JSON ETags and file oids
    reproduced byte for byte;
  - users `Orosius` (`persona-owner`) and `TestingBOrig` (`persona-requester`, pending);
  - clone-only demos: `Orosius/gated-auto-demo`, `Orosius/gated-form-demo`, `Orosius/not-gated-demo`
    and the user `DemoCarol` (`persona-carol`).

## Layout (`src/clone/`)

| Module | Role |
|---|---|
| `domain.py` | pure rules: the access decision (ACC-*), gate messages, and the handle / batch / grant / ask-access / cancel transitions |
| `store.py` | in-memory state, seed load/validate/dump, virtual clock, ids, outbox, log |
| `protocol.py` | wire protocol: routing, check order, error formats, ETags, redirects |
| `zod.py` | HF's zod-style validation messages (pretty body + ASCII-sanitised header) |
| `files.py` | siblings, tree, LFS metadata, deterministic stub bytes |
| `exchange_log.py` | log entries in the bridge's schema |
| `app.py`, `main.py` | FastAPI app, control endpoints, entry point |

## Known gaps

Orgs and org-member bypass are not modelled (`orgMembersGated` is stored only). Neither are
read-only or fine-grained tokens. `/revision/`, `/raw/` and `/blob/` are outside the surface. File
contents that were not recorded are stubs. Rejection reasons are validated, then discarded (no
observed API exposes them). Every choice where the KB is silent is marked `Provisional (Q-n)` in the
code and listed in [../docs/hf-gated/open-questions.md](../docs/hf-gated/open-questions.md).
