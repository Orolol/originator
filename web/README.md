# web

Next.js (App Router) replica of Hugging Face's gated-model screens: the requester gate box on
`/{ns}/{repo}` and the owner's "Gated user access" section plus "Manage access requests" modal on
`/{ns}/{repo}/settings`. It talks to `BACKEND_URL` (bridge or clone) only; the contract is
[../docs/system.md](../docs/system.md), the screens [../docs/hf-gated/ui.md](../docs/hf-gated/ui.md).

## Run

The backend first (from the repo root): `uv run --project bridge bridge` (port 8100).

```bash
npm install
npm run dev          # http://localhost:3000 ; BACKEND_URL defaults to http://127.0.0.1:8100
```

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
| `src/lib/gateState.ts` | the only auth-check → gate-state mapping |
| `src/lib/gateForm.ts` | `extra_gated_*` card metadata → form config |
| `src/lib/hubClient.ts` | browser-side requests fired by the owner controls |

Provisional choices are marked `// Provisional (Q-n)` in the code.
