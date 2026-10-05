# System: web ⇄ backend (bridge | clone)

One web app, two interchangeable backends. The web app never knows which one it talks to: it only
knows `BACKEND_URL`. Both backends speak the **Hugging Face wire protocol** for the slice
([hf-gated/api.md](hf-gated/api.md)), so the same web app, the same scenario scripts and the
official `huggingface_hub` client (with `HF_ENDPOINT`) drive either one.

```
browser ──► web (Next.js, :3000) ──► BACKEND_URL ──┬─► bridge (Python, :8100) ──► https://huggingface.co
            pages at HF paths                      └─► clone  (Python, :8200, planned; in-memory)
            /api/* and web routes proxied
```

## Personas (identity)

HF identifies callers by `Authorization: Bearer <token>`. The web app acts as one **persona** at a
time, chosen with a cookie. It sends the persona's **fake token** to the backend; it never holds real
HF tokens.

| Persona | Token sent by web | Bridge maps to | Clone (planned) seeds |
|---|---|---|---|
| `anonymous` | no `Authorization` header | forwarded anonymously | anonymous |
| `owner` | `persona-owner` | `.env` `HF_OWNER_ACCESS_TOKEN` (HF user `Orosius`) | user `Orosius` |
| `requester` | `persona-requester` | `.env` `HF_REQUESTER_ACCESS_TOKEN` (HF user `TestingBOrig`) | user `TestingBOrig` |

Any other bearer value → `401`, JSON `{"error": "Invalid credentials in Authorization header"}`,
with the same text in `X-Error-Message` (HF's own wording, per `huggingface_hub`'s `_http.py`).

## Backend surface (both backends)

Only these routes exist. `{repo}` = `{ns}/{name}`. Query strings are forwarded verbatim (for
example `expand[]=gated`).

| Method | Path | Notes |
|---|---|---|
| GET | `/api/whoami-v2` | persona identity (web header shows the username) |
| GET | `/api/quicksearch` | user search for "Add access" (`?q=…&type=user`) |
| GET | `/api/models/{repo}` | model info (`gated`, `cardData`, `siblings`…) |
| GET | `/api/models/{repo}/tree/{rev}` (optionally `/{path}`) | file list |
| GET | `/api/models/{repo}/auth-check` | requester gate-state source (see below) |
| PUT | `/api/models/{repo}/settings` | gating config; the response echoes only the fields sent [OBS] |
| GET | `/api/models/{repo}/user-access-request/{pending\|accepted\|rejected\|reset}` | owner lists |
| POST | `/api/models/{repo}/user-access-request/{handle\|grant\|batch\|cancel}` | owner actions; `cancel` = requester self-cancel |
| POST | `/{repo}/ask-access` | requester submits the gate form → `303` to the repo page |
| GET | `/{repo}/user-access-report` | report download |
| GET, HEAD | `/{repo}/resolve/{rev}/{path}` | file download (gate applies) |

Responses keep HF's status codes, bodies and these headers: `Content-Type`, `Content-Disposition`,
`X-Error-Code`, `X-Error-Message`, `WWW-Authenticate`, `Link`, `Location`, `X-Total-Count`,
`X-Repo-Commit`, `ETag`. `Set-Cookie` is never forwarded.

**URL rewriting**: absolute `https://huggingface.co` URLs in `Location` and `Link` are rewritten to
the backend's own public URL, so pagination and redirects stay on the backend. A redirect to another
host (a CDN) is left untouched. This is the only normalisation the bridge applies.

## Control endpoints (not part of HF's surface)

| Backend | Path | Purpose |
|---|---|---|
| bridge | `GET /__bridge__/health` | upstream, configured personas, allowed repos |
| bridge | `GET /__bridge__/log?limit=N`, `DELETE /__bridge__/log` | exchange log (tokens never logged) |
| clone (planned) | `/__clone__/reset`, `/__clone__/seed`, `/__clone__/clock`, `/__clone__/outbox` | determinism and inspection |

## Bridge safety rules

- **Repo allowlist** (`BRIDGE_REPOS`, default `Orosius/deltanet-mla-latent`). Repo-scoped calls on
  any other repo → `403`, `X-Error-Code: BridgeRepoNotAllowed`.
- Routes outside the table → `404`, `X-Error-Code: BridgeRouteNotAllowed`.
- No retries and no redirect following; one upstream call per incoming call, so the log reflects
  exactly the requests fired.

## Web app conventions

- **Same URLs as huggingface.co**: `/{ns}/{name}` (model page with the gate box), `/{ns}/{name}/settings`
  (owner settings). Hence a Playwright walkthrough written for huggingface.co can run on the web
  app by changing the base URL.
- **Same requests fired**: the browser calls `/api/…` and the web routes (`/{repo}/ask-access`,
  `/{repo}/user-access-report`, `/{repo}/resolve/…`) on the web origin, and the web server proxies
  them to `BACKEND_URL` with the persona token.
- **Same accessible structure**: real `<button>`, `<select>`, `<a>`, `role="dialog"`,
  `role="tablist"`/`tab` with HF's exact labels, so `getByRole(…, {name})` selectors work on both
  sites. No styling work.
- Persona switch: `GET /-/persona?as=<persona>&next=<path>` sets the cookie and redirects.
  (Folders starting with `_` are private in the Next.js App Router, hence `/-/`.)
- Requester gate state comes from `auth-check`, because the API has no "my request status" endpoint:
  `200` → access; `401 GatedRepo` → anonymous; `403 GatedRepo` with the "not in the authorized
  list" message → no request (or reset [Q-5]); "awaiting a review" → pending; any other message
  → shown verbatim and flagged as unmapped (rejected is not yet recorded [Q-8]).

## Known bridge-mode gaps

- Notification settings (`gatedNotificationsMode`, `gatedNotificationsEmail`) are **not readable**
  through the API: there is no GET settings, and the PUT echoes only the fields sent. The settings
  screen shows defaults until changed in-session. The clone can do better, but it must not diverge
  from HF's wire protocol to do so.
- The HF UI reads request status from server-side page props; we infer it from `auth-check`
  messages (see above).
