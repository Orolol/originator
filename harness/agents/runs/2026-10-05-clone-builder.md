# Run: clone builder (2026-10-05)

- Agent type: general-purpose subagent, model **Opus**, background, in parallel with the blind
  conformance verifier.
- Inputs it relied on: `AGENTS.md`, `docs/system.md` (clone contract), `docs/hf-gated/*`, the
  recorded observations.
- Output: `clone/`.

## Prompt (verbatim)

You are implementing the **clone** in `/home/orosius/workspace/originator`: a deterministic, resettable, in-memory reimplementation of Hugging Face's "gated models" access-request backend. It replaces the bridge (a proxy to the real huggingface.co) behind the exact same wire protocol, so the same web UI, the same scenario scripts and the official `huggingface_hub` client work against it unchanged. Fidelity is graded: same status codes, bodies, headers and state transitions as the real Hub — weird edge cases included.

## Read first (mandatory, in this order)
1. `AGENTS.md` — hard rules (never edit `writeup.md`; **no invented behaviour**: every behaviour traces to a rule ID or is marked provisional; in-memory only, no DB/disk store).
2. `docs/system.md` — the backend surface, personas, and the **"Clone (Python, :8200): contract"** section (control endpoints, virtual clock, seed format, built-in seeds, outbox, log schema). Follow it exactly.
3. `docs/hf-gated/behaviour.md` — the rules (CFG-*, ACC-*, REQ-*, REV-*, TS-*, REP-*). Most are now [OBS] (observed on the real Hub on 2026-10-05).
4. `docs/hf-gated/api.md` — wire protocol: paths, payloads, error headers (`X-Error-Code`, `X-Error-Message`, `WWW-Authenticate`), exact messages, validation-message format (zod pretty body vs ASCII-sanitised header), check order.
5. `docs/hf-gated/gate-form.md` (card metadata, field types) and `docs/hf-gated/open-questions.md` (what is UNKNOWN; provisional choices table).
6. The recorded fixtures — these are ground truth, mirror them byte-for-byte where they show something: `docs/hf-gated/observations/*.json` (probe format: `records[]` with `method`, `url`, `as`, `request_body`, `status`, `headers`, `body_json`/`body_excerpt`/`body_text`), especially `2026-10-05-owner-walkthrough.json`, `2026-10-05-owner-walkthrough-completion.json`, `2026-10-05-clone-seed-reads.json` (model info, tree, whoami, small files with ETag/X-Repo-Commit/Content-Disposition), `2026-10-05-anonymous-probes.json`, `2026-10-05-requester-ask-access.json`, `2026-10-05-ui-walkthrough.json` (bridge log of a live UI walkthrough).

## What to build: `clone/` (uv project, Python 3.12, FastAPI)
- `clone/pyproject.toml` (deps: fastapi, uvicorn; dev group: pytest, httpx), `uv python pin 3.12`, `src/clone/` layout, console script `clone = "clone.main:run"` → `uv run --project clone clone` serves on `127.0.0.1:8200` (`CLONE_HOST`/`CLONE_PORT` override; `CLONE_PUBLIC_URL` default `http://127.0.0.1:8200` for absolute URLs like the ask-access `Location`). Create `uv.lock` via `uv sync`.
- Architecture (keep it small and readable): a pure **domain module** (state machine + access decision, no HTTP), a **store** (in-memory state + seed load/dump + virtual clock + id counter), an **HTTP layer** mapping the wire protocol onto the domain (errors with exact status/body/headers), **seeds** (built-in seed documents, built from the fixtures — commit the generated seed JSON under `src/clone/seeds/` and the small script that derived it from the fixtures), and the **control endpoints** + exchange log + outbox. Cite rule IDs in comments where a rule is implemented (e.g. `# REV-1: same-status → 404, identical to "no request"`).
- Implement the full backend surface of docs/system.md: whoami-v2, quicksearch (provisional: users by case-insensitive prefix on username/fullname — Q-25; shape per HF OpenAPI `{"users":[{_id, avatarUrl, fullname, user}], …}`), model info (incl. `expand[]=…` → `_id`, `id` + requested fields only [OBS model-info-expand]), tree (top-level and subpaths; synthesize deterministic entries for files whose oid/size the fixtures don't give), auth-check, settings PUT (echo semantics CFG-3/CFG-7: echo `gated`/`private`/`visibility` sent; notification fields stored but NOT echoed), the four lists (limit 10–1000 validation, `q` case-insensitive substring/prefix over username/fullname/email — provisional per Q-21, `after`/`before`, `Link: <…>; rel="next"` pagination when more than `limit`), handle (incl. `userId`, reasons, reset), grant, batch (per-item outcomes, same-status = ok:true), requester self-cancel (`…/user-access-request/cancel`, provisional per Q-3: delete the caller's request → "no request"; 404 "No access request found matching your criteria" if none), ask-access (JSON **and** form-encoded bodies; stores `fields` from extra_gated_fields keys present; 303 `Location: {CLONE_PUBLIC_URL}/{repo}` + text body `See Other. Redirecting to {location}`; manual → pending, auto → accepted (email shared), pending/rejected → no-op 303 [OBS], reset → new pending with new timestamp [OBS]; anonymous → provisional 401 as HF auth), user-access-report (JSON, `Content-Disposition: attachment; filename=user-access-report-{ns}-{name}.json`, entries `{fullname, user, email, time, status}` + `reviewedAt` when set, provisional), resolve GET/HEAD (ACC-1..ACC-7: allowlist exact names at root, gate-before-existence, 401 anonymous vs 403 with the per-status messages, 404 EntryNotFound/RevisionNotFound when allowed, headers Content-Type/Content-Disposition/ETag/X-Repo-Commit/Content-Length as recorded; non-gated → 307 to `/api/resolve-cache/models/{repo}/{sha}/{path}?…` as recorded; LFS files: provisional 302 to a clone-local URL with `X-Linked-Size`/`X-Linked-Etag`), and `/api/resolve-cache/…`.
- Error semantics exactly per api.md §3 (status, `X-Error-Code` only where HF sends one, `X-Error-Message`, JSON `{"error": …}` on /api, text/plain on web routes like resolve, `WWW-Authenticate` on 401s), including the zod-style validation messages (body `✖ …\n  → at <path>`, header ASCII-sanitised: non-ASCII → `*`, whitespace runs → one space) and the check order in api.md.
- Control endpoints, virtual clock, deterministic ids, outbox and exchange log exactly per docs/system.md (log entries use the bridge's schema; `started_at` from the virtual clock; `duration_ms` 0; `upstream` false).
- Built-in seeds per docs/system.md: `sandbox` (default; mirrors the recorded real repo: model-info fields, the 1018 siblings, recorded tree entries, real small-file contents with their recorded ETag/oid; TestingBOrig **pending**), plus the clone-only demo repos and `DemoCarol`. Unknown file contents → deterministic stub bytes.
- Personas/auth: tokens come from the seed (`persona-owner`, `persona-requester`, `persona-carol`); unknown bearer or missing auth on protected routes → 401 `Invalid username or password.` + `WWW-Authenticate` exactly as recorded.

## Tests (yours — implementation-level, fast, offline)
`clone/tests/`: domain unit tests (state machine matrix from behaviour.md §5.1, access decision ACC-*, timestamps TS-*), HTTP tests via FastAPI TestClient for the error matrix and headers, determinism (same sequence twice from reset → identical log/outbox/responses), seed round-trip (`GET /__clone__/state` → `PUT` → same), and a **fixture smoke**: replay the HTTP requests of `2026-10-05-owner-walkthrough-completion.json` from the matching initial state and assert status codes + `X-Error-Message` match. Keep tests meaningful, parametrized, few. Note: a separate verifier agent is concurrently writing an independent black-box conformance suite in `conformance/` — do not read or modify it, and don't try to game it; your job is fidelity to the KB.

## Constraints
- In-memory only: no files written at runtime, no DB. Seeds are read-only package data.
- Never call the real huggingface.co (no network at all). Never read or print `.env`.
- Only create/modify files under `clone/`. Do not touch `bridge/`, `web/`, `conformance/`, `docs/`, `harness/`, `writeup.md`, `AGENTS.md`. No `git add`/`commit`.
- If you start the server for a manual smoke test, use port **8299** (`CLONE_PORT=8299`) — port 8200 is reserved for the verifier — and stop it afterwards.
- Don't invent: where the KB is silent, choose the simplest behaviour consistent with it, mark `# Provisional (Q-n): …`, and list it in your report.

## Done when
`uv run --project clone pytest clone/tests` passes; the server starts and `/__clone__/health` answers; `PUT /__clone__/state` + `GET` round-trips; the completion-walkthrough fixture smoke passes.

## Final report (short)
How to run; module layout; test counts; **list of provisional choices with Q-ids**; any place where fixtures and docs disagreed and what you followed; known gaps.
