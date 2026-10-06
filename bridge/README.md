# bridge

Thin Python HTTP proxy between the web UI and the real <https://huggingface.co>. It speaks the
Hugging Face wire protocol for the gated-models slice and is later replaced by the in-memory clone
behind the same contract. The contract is [../docs/system.md](../docs/system.md) (personas, route
table, header passthrough, URL rewriting); this file only covers running and configuring it.

## Run

```bash
uv run --project bridge bridge        # from the repo root; serves http://127.0.0.1:8100
curl -s localhost:8100/__bridge__/health
```

## Configuration

Environment variables, plus the repo-root `.env` (the process environment wins; set
`BRIDGE_ENV_FILE` to read another file).

| Variable | Default | Meaning |
|---|---|---|
| `BRIDGE_UPSTREAM` | `https://huggingface.co` | Hub origin to forward to |
| `BRIDGE_PUBLIC_URL` | `http://127.0.0.1:8100` | origin that replaces the upstream one in `Location` / `Link`; set it if you change host or port |
| `BRIDGE_REPOS` | `OwnerOfTheGatedModel/tiny-gated-model` | comma-separated repo allowlist |
| `BRIDGE_HOST`, `BRIDGE_PORT` | `127.0.0.1`, `8100` | where uvicorn listens |
| `BRIDGE_LOG_FILE` | `<repo>/harness/recordings/raw/bridge.jsonl` | JSONL exchange log (gitignored); empty string disables it |
| `HF_OWNER_ACCESS_TOKEN` | none | real token behind `Bearer persona-owner` |
| `HF_REQUESTER_ACCESS_TOKEN` | none | real token behind `Bearer persona-requester` |

## Behaviour in short

- Only the routes in `docs/system.md` are forwarded. Order of checks: route (404
  `BridgeRouteNotAllowed`), repo allowlist (403 `BridgeRepoNotAllowed`), `Authorization`
  (401 for anything but `persona-owner` / `persona-requester`; a persona whose token is not
  configured gives 503 `BridgePersonaNotConfigured` rather than falling back to anonymous).
  Rejected calls never reach the Hub.
- One upstream call per incoming call: no retries, no redirect following, no cookies in either
  direction. Upstream failures are 502 / 504 (`BridgeUpstreamError` / `BridgeUpstreamTimeout`).
- Control endpoints (not logged themselves): `GET /__bridge__/health`,
  `GET /__bridge__/log?limit=N` (JSON array, newest last, default 100), `DELETE /__bridge__/log`
  (empties the in-memory log; the JSONL file is append-only and is kept).
- The log never contains the `Authorization` header or real token values.

## Safety rules

- State-changing calls (`PUT settings`, `handle`, `grant`, `batch`, `cancel`, `ask-access`) go to
  the live Hub only when someone chooses to, and only on the sandbox repo. They email the repo
  owner. The test suite never sends any of them upstream.
- Tokens come from `.env` only. Never print them or commit them.

## Tests

```bash
uv run --project bridge pytest bridge/tests          # fast, offline (mocked upstream); live tests are deselected
uv run --project bridge pytest bridge/tests -m live  # read-only smoke tests against the real Hub (GET/HEAD only)
```

Plain `uv run --project bridge pytest` from the repo root also works (live tests are skipped
there too), but pytest then ignores this project's config, so prefer the explicit path or
`uv run --directory bridge pytest`.
