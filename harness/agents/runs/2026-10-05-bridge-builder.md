# Run: bridge builder (2026-10-05)

- Agent type: general-purpose subagent, model **Sonnet**, background, in parallel with the UI builder.
- Inputs it relied on: `AGENTS.md`, `docs/system.md`, `docs/hf-gated/api.md`.
- Output: `bridge/`.

## Prompt (verbatim)

You are implementing the **bridge** of a take-home project in `/home/orosius/workspace/originator` (a replication of Hugging Face's "gated models" access-request feature). The bridge is a thin Python HTTP proxy between our web UI and the real https://huggingface.co. Later an in-memory clone will replace it behind the same contract.

## Read first (mandatory)
1. `AGENTS.md` (hard rules — especially: never edit `writeup.md`; never print/log secrets; no state-changing calls on the live Hub).
2. `docs/system.md` — **the contract you implement** (personas, route table, header passthrough, URL rewriting, control endpoints, safety rules). Follow it exactly.
3. `docs/hf-gated/api.md` (wire protocol, error headers) — for context.

## What to build: `bridge/` (a uv-managed Python project)
- `bridge/pyproject.toml`: name `bridge`, `requires-python = ">=3.12"`, deps: `fastapi`, `uvicorn`, `httpx`. Dev deps (uv dependency group `dev`): `pytest`, `pytest-asyncio` only if you need it (prefer FastAPI `TestClient` + `httpx.MockTransport`, no respx). Console script `bridge = "bridge.main:run"` so that `uv run --project bridge bridge` starts uvicorn on `127.0.0.1:8100` (host/port overridable via `BRIDGE_HOST`/`BRIDGE_PORT`). Use a `src/bridge/` layout. Pin Python with `uv python pin 3.12` inside `bridge/` (3.12 is installed). Commit nothing; but do create `bridge/uv.lock` via `uv sync`.
- Config (env vars, plus loading the **repo-root** `.env` file — locate the repo root relative to the package file or via `BRIDGE_ENV_FILE`; parse KEY=VALUE lines yourself or with python-dotenv, your call):
  - `BRIDGE_UPSTREAM` default `https://huggingface.co`
  - `BRIDGE_PUBLIC_URL` default `http://127.0.0.1:8100` (used for Location/Link rewriting)
  - `BRIDGE_REPOS` comma-separated allowlist, default `Orosius/deltanet-mla-latent`
  - persona tokens: `persona-owner` → env `HF_OWNER_ACCESS_TOKEN`, `persona-requester` → env `HF_REQUESTER_ACCESS_TOKEN` (both exist in the root `.env`; never print their values — not in logs, errors, health, tests output, or your final report).
  - `BRIDGE_LOG_FILE` default `<repo-root>/harness/recordings/raw/bridge.jsonl` (that directory is gitignored; create it if missing). Empty string disables the file.
- Behaviour (see docs/system.md for the authoritative list):
  - A route table of allowed (method, path regex) pairs exactly as in docs/system.md "Backend surface". `{repo}` is `ns/name` (HF names may contain `-`, `_`, `.`). `resolve` paths can contain slashes. HEAD must work on resolve.
  - Repo-scoped routes on a repo not in `BRIDGE_REPOS` → 403 JSON `{"error": "Repo not allowed by bridge: <repo>"}` with `X-Error-Code: BridgeRepoNotAllowed`. Unknown route/method → 404 JSON with `X-Error-Code: BridgeRouteNotAllowed`. `whoami-v2` and `quicksearch` are not repo-scoped.
  - Auth: no `Authorization` header → forward anonymously. `Bearer persona-owner|persona-requester` → replace with the real token. Any other Authorization value → 401 JSON `{"error": "Invalid credentials in Authorization header"}` + `X-Error-Message` with the same text (do not call upstream).
  - Forward: method, path, raw query string verbatim (keep `expand[]=x` exactly), request body bytes, and `Content-Type`/`Accept` headers. Use one `httpx.AsyncClient` with `follow_redirects=False`, no retries, a sane timeout. Do not forward cookies or other client headers. Set a `User-Agent` like `originator-bridge/0.1`.
  - Response: same status code and body bytes; only these headers: `Content-Type`, `Content-Disposition`, `X-Error-Code`, `X-Error-Message`, `WWW-Authenticate`, `Link`, `Location`, `X-Total-Count`, `X-Repo-Commit`, `ETag`. Never `Set-Cookie`. In `Location` and `Link`, rewrite absolute URLs whose origin is the upstream origin to `BRIDGE_PUBLIC_URL` (relative URLs and other hosts, e.g. CDN redirects, untouched). Expose these headers via CORS `Access-Control-Expose-Headers` is NOT needed (the web calls the bridge server-side) — skip CORS.
  - Control endpoints: `GET /__bridge__/health` → `{"ok": true, "upstream": ..., "public_url": ..., "repos": [...], "personas": {"owner": <bool configured>, "requester": <bool>}}`; `GET /__bridge__/log?limit=N` (default 100, newest last) and `DELETE /__bridge__/log`.
  - Exchange log: in-memory `deque(maxlen=1000)` + JSONL append. Entry: `id` (incrementing int), `started_at` (ISO UTC ms), `duration_ms`, `persona` (`anonymous`/`owner`/`requester`), `method`, `path`, `query`, `request_body` (parsed JSON, or parsed form, or None; strings truncated to 2000 chars), `status`, `response_headers` (the kept subset), `response_body` (parsed JSON if JSON, else text excerpt ≤ 2000 chars; for binary/large file bodies just `{"bytes": n}`). **Never log real tokens or the Authorization header.** Rejected calls (route/repo/auth) are logged too, with `upstream: false`.
- Tests in `bridge/tests/` (fast, offline, default run): use an injectable upstream transport (`httpx.MockTransport`) so tests never hit the network. Cover: persona mapping (owner/requester/anonymous/unknown→401 without upstream call), real token actually sent upstream for personas and never present in log/response, status/body/header passthrough incl. `X-Error-Code`/`X-Error-Message`, `Set-Cookie` stripped, `Location` rewrite on a 303 from `/{repo}/ask-access`, `Link` rewrite for pagination, CDN `Location` untouched, query string verbatim (`expand[]=gated&expand[]=cardData`), repo allowlist 403, route allowlist 404 (e.g. `DELETE /api/models/{repo}` or `/api/models/{repo}/discussions`), HEAD on resolve, PUT/POST body forwarding (JSON and form-encoded), log entries & `DELETE /__bridge__/log`. Prefer a few parametrized tests over many near-duplicates.
- Live smoke tests: `bridge/tests/test_live.py`, marked `@pytest.mark.live`, **skipped by default** (configure pytest `addopts = "-m 'not live'"` and register the marker). They may only use **GET/HEAD** against the real Hub through the bridge app (in-process with the real transport): whoami as owner → name `Orosius`; whoami as requester → name `TestingBOrig`; owner `GET .../user-access-request/pending` → 200 list; requester `GET .../auth-check` → 403 with `X-Error-Code: GatedRepo`; anonymous resolve of `.gitattributes` → 401 GatedRepo; anonymous resolve `README.md` → 200. Do not assert exact list contents (state may change). Run them once with `uv run --project bridge pytest -m live` and report results.
- `bridge/README.md`: what it is, run command, env vars, safety rules, how to run fast vs live tests. Short.

## Hard constraints
- **Absolutely no non-GET/HEAD request to the live huggingface.co** — not through the bridge, not with curl, not in tests. No `PUT settings`, no `handle`, `grant`, `batch`, `cancel`, `ask-access`. Those are reserved for the orchestrator. Mocked tests can exercise them freely.
- Never print the token values (don't `cat .env`; if you need to check presence, print only key names).
- Do not modify anything outside `bridge/` except creating `harness/recordings/raw/` if needed. Do not touch `web/` (another agent is building it concurrently), `docs/`, `writeup.md`, `AGENTS.md`. Do not run `git add`/`git commit`.
- Match the project's style: small, readable modules, comments only where they carry information (cite rule/contract when relevant). Fail explicitly rather than silently.

## Done when
`uv run --project bridge pytest` passes offline; live read-only smoke passes; `uv run --project bridge bridge` starts and `curl -s localhost:8100/__bridge__/health` works (stop the server afterwards — do not leave it running).

## Final report (keep it short)
Files created; how to run; test results (fast + live, with counts); any deviation from docs/system.md and why; anything surprising you observed from the live Hub (e.g. headers you didn't expect). No token values.
