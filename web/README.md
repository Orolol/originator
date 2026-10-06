# web

Next.js (App Router) replica of Hugging Face's gated-model screens: the requester gate box on
`/{ns}/{repo}` and the owner's "Gated user access" section plus "Manage access requests" modal on
`/{ns}/{repo}/settings`. It talks to one backend at a time, the clone or the bridge, chosen in the header; the contract is
[../docs/system.md](../docs/system.md), the screens [../docs/hf-gated/ui.md](../docs/hf-gated/ui.md).

## Run

Start the backends first, from the repo root: the clone with `uv run --project clone clone` (port
8200) and/or the bridge with `uv run --project bridge bridge` (port 8100).

```bash
npm install
npm run dev          # http://localhost:3000
```

The header has a backend switch, `Backend: clone | bridge`, which sets the `backend` cookie through
`/-/backend?to=clone|bridge&next=…`. **clone** is the default: local, in-memory, resettable. **bridge**
is the live huggingface.co, so writes reach the real Hub. Use `CLONE_URL` / `BRIDGE_URL` to move them;
`BACKEND_URL` pins one URL and disables the switch.

While the clone is selected, a **Reset clone** button (`POST /-/clone/reset` → the clone's
`POST /__clone__/reset`) restores its default seed and reloads the page. The button is hidden on
the bridge, and the route refuses there.

Pick a persona with `/-/persona?as=anonymous|owner|requester&next=/Orosius/deltanet-mla-latent`
(or the links in the header).

## Tests

```bash
npm test             # vitest, offline (fetch mocked)
npm run test:e2e     # Playwright, READ-ONLY against the live backend; builds and serves on :3100
npm run lint
npm run build
```

The e2e suite aborts (and fails on) any non-GET/HEAD browser request, so it cannot change Hub
state. It uses the system Chrome (`PLAYWRIGHT_CHANNEL=chrome` by default).

## Layout

| Path | What |
|---|---|
| `src/app/[ns]/[repo]/page.tsx` | model page: gate box (A1–A3) + file list |
| `src/app/[ns]/[repo]/settings/page.tsx` | owner settings section (B1–B3) |
| `src/app/api/[...path]/route.ts` | `/api/*` proxy to the backend with the persona token |
| `src/app/[ns]/[repo]/{ask-access,user-access-report,resolve/[...rest]}/route.ts` | HF web routes, proxied |
| `src/app/-/persona/route.ts` | persona switch (cookie) |
| `src/app/-/cancel-request/route.ts` | requester self-cancel from A3 → `POST /api/models/{repo}/user-access-request/cancel` (provisional, Q-3) |
| `src/lib/gateState.ts` | the only auth-check → gate-state mapping |
| `src/lib/gateForm.ts` | `extra_gated_*` card metadata → form config |
| `src/lib/hubClient.ts` | browser-side requests fired by the owner controls |

Provisional choices are marked `// Provisional (Q-n)` in the code.

## Scripted walkthrough against the clone

```bash
npm --prefix web run test:e2e:clone
```

`playwright.clone.config.ts` starts the clone on `127.0.0.1:8201` and a production build on `:3101`
(`BACKEND_URL` must be a `127.0.0.1:82xx` clone; the guard refuses anything else). The test replays the
journey of the live UI walkthrough using role/label selectors only, then diffs the clone's request log
against the live recording (`harness/kb/compare_logs.py`); the report is `e2e/out/clone-vs-live.md`.
Writes happen here because the clone is local. The default `playwright.config.ts` ignores this spec.
