# System: web ⇄ backend (bridge | clone)

One web app, two interchangeable backends. The web app never knows *how* a backend works: it only
knows each backend's base URL, and the browser picks one with a switch in the header (below). Both
backends speak the **Hugging Face wire protocol** for the slice
([hf-gated/api.md](hf-gated/api.md)), so the same web app, the same scenario scripts and the
official `huggingface_hub` client (with `HF_ENDPOINT`) drive either one.

```
browser ──► web (Next.js, :3000) ──► chosen backend ──┬─► bridge (Python, :8100) ──► https://huggingface.co
            pages at HF paths                         └─► clone  (Python, :8200; in-memory)
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

Any other bearer value → `401`, JSON `{"error": "Invalid username or password."}`, with the same text in
`X-Error-Message` and `WWW-Authenticate: Bearer realm="Authentication required", charset="UTF-8"`. That
is exactly what HF answers for an invalid token and for anonymous calls to protected routes
[OBS 2026-10-05, `hf-gated/observations/2026-10-05-clone-seed-reads.md`].

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
| GET | `/{repo}/raw/{rev}/{path}` | raw file, gate without allowlist (ACC-10) |
| GET | `/{repo}/blob/{rev}/{path}` | file page (HTML), gated like `raw` (ACC-5); the clone renders a minimal page |

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
- Bridge-generated errors (as implemented) are JSON `{"error"}` with `X-Error-Message` and an
  `X-Error-Code` starting with `Bridge…`: `BridgeRouteNotAllowed` (404), `BridgeRepoNotAllowed`
  (403), `BridgePersonaNotConfigured` (503, so a missing token never silently becomes anonymous),
  `BridgeUpstreamError` (502), `BridgeUpstreamTimeout` (504). Paths with `.`/`..` segments are
  refused (404), and upstream cookies are never stored.
- Responses are buffered, and HEAD responses carry only the kept headers (no `Content-Length` or
  `X-Linked-*`). Widen the list before driving `hf_hub_download` through the bridge.

## Web app conventions

- **Same URLs as huggingface.co**: `/{ns}/{name}` (model page with the gate box), `/{ns}/{name}/settings`
  (owner settings). Hence a Playwright walkthrough written for huggingface.co can run on the web
  app by changing the base URL.
- **Same requests fired**: the browser calls `/api/…` and the web routes (`/{repo}/ask-access`,
  `/{repo}/user-access-report`, `/{repo}/resolve/…`) on the web origin, and the web server proxies
  them to the chosen backend with the persona token.
- **Backend switch**: a `backend` cookie (`clone` | `bridge`), set by
  `GET /-/backend?to=<backend>&next=<path>` (links in the header), selects the backend per browser.
  The default is `clone`, so nothing reaches the real Hub unless the bridge is chosen explicitly. The
  header says which backend answers and flags the bridge as live. URLs come from `CLONE_URL` (default
  `http://127.0.0.1:8200`) and `BRIDGE_URL` (default `http://127.0.0.1:8100`). **`BACKEND_URL`, when
  set, pins every request to it and disables the switch** (`/-/backend` → 409). Both e2e configs pin:
  the read-only one to the bridge, and the clone walkthrough, which writes, to its own clone.
- **Reset clone** (header button, shown only while the clone is selected and nothing is pinned): a
  form `POST /-/clone/reset` that calls the clone's `POST /__clone__/reset` (default seed) and
  redirects back. It refuses with 409 when the bridge is selected or a backend is pinned, so it can
  never be aimed at the real Hub.
- **Same accessible structure**: real `<button>`, `<select>`, `<a>`, `role="dialog"`,
  `role="tablist"`/`tab` with HF's exact labels, so `getByRole(…, {name})` selectors work on both
  sites. No styling work.
- The web proxy rewrites the chosen backend's absolute URLs in `Location` and `Link` to the web
  origin. This only works if each backend's public URL (`BRIDGE_PUBLIC_URL`, `CLONE_PUBLIC_URL`)
  equals the web app's URL for it exactly (`127.0.0.1` ≠ `localhost`). The file list comes from `siblings`, which is recursive, rather than `/tree/main`.
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

## Clone (Python, `:8200`): contract

The clone implements the **backend surface** above (same paths, payloads, status codes, `X-Error-*`
headers, bodies) from [hf-gated/behaviour.md](hf-gated/behaviour.md) and [hf-gated/api.md](hf-gated/api.md),
entirely **in memory**, plus `GET /api/resolve-cache/models/{repo}/{sha}/{path}` (target of the 307 that a
non-gated repo's `resolve` returns, CFG-6). A process restart or `POST /__clone__/reset` restores the
default seed.

### Determinism

- **Virtual clock**, never the wall clock. It starts at the seed's `now`. Each request that **changes
  state** advances it by `tick_ms` (seed field, default `1000`) *before* stamping `timestamp` /
  `reviewedAt`; reads do not advance it.
- **IDs**: 24-hex ObjectId-like strings from a counter. Seeded IDs are kept verbatim.
- **Ordering**: lists in a stable order (provisional until Q-10 is recorded: by `timestamp`
  ascending, then insertion order).
- Same seed + same request sequence ⇒ byte-identical responses, log and outbox.

### Control endpoints (reserved prefix `/__clone__/`, never part of HF's surface)

| Method | Path | Effect |
|---|---|---|
| GET | `/__clone__/health` | `{"ok": true, "seed": <name>, "now": <clock>}` |
| POST | `/__clone__/reset` | body optional `{"seed": "<built-in seed name>"}` (default `sandbox`); clears log and outbox |
| GET | `/__clone__/state` | full state, in the seed format below (round-trips with PUT) |
| PUT | `/__clone__/state` | replace the whole state with a seed document; clears log and outbox |
| GET / POST | `/__clone__/clock` | read; or set `{"now": iso}` / `{"advance_ms": n}` |
| GET / DELETE | `/__clone__/outbox` | e-mails HF would send (see below) |
| GET / DELETE | `/__clone__/log` | exchange log, **same entry schema and key order as `/__bridge__/log`** (as the bridge emits it: `id, started_at, duration_ms, persona, method, path, query, upstream, request_body, status, response_headers, response_body`), with `started_at` from the virtual clock and `duration_ms` = 0, so `harness/kb/bridge_log_to_md.py` and diffs work on both backends |

Outbox entry: `{"id", "at", "to": <email>, "kind", "repo", "user", "reason"?}`, where `kind` is one of
`"new_request"` (to the notification recipient, manual mode only: `gatedNotificationsEmail`, else the
owner's email) and `"request_reset"` (to the requester, with `resetReason`). Only effects documented in
behaviour.md §7 are emitted. Whether HF also e-mails on accept/reject is unknown (Q-20).

### Seed format (`PUT /__clone__/state`, `GET /__clone__/state`, built-in seeds)

```jsonc
{
  "seed": "sandbox",                       // name, informational
  "now": "2026-10-05T14:30:00.000Z",       // virtual clock
  "tick_ms": 1000,
  "users": [
    {"user": "Orosius", "_id": "63ea055c74f940d171e52701", "fullname": "Gaetan Martin",
     "email": "orosius@example.com", "avatarUrl": "/avatars/321442c65614e6e52fb158f334e9bb1e.svg",
     "isPro": true, "token": "persona-owner", "orgs": []},
    {"user": "TestingBOrig", "_id": "6ac3a4b8792f9017b6cb67ec", "fullname": "Bridge",
     "email": "testingborig@example.com", "avatarUrl": "/avatars/eccbd8a248c3753b1ba445d9b80ee712.svg",
     "isPro": false, "token": "persona-requester", "orgs": []}
  ],
  "repos": [
    {"id": "Orosius/deltanet-mla-latent", "_id": "69414ed409f9267fc5b494e2", "author": "Orosius",
     "private": false, "gated": "manual", "orgMembersGated": false,
     "gatedNotificationsMode": "bulk", "gatedNotificationsEmail": null,
     "sha": "6f1dade6f974de81ce21aa14b87add2e0217b05e",
     "createdAt": "2025-12-16T12:21:40.000Z", "lastModified": "2026-01-01T02:52:44.000Z",
     "cardData": {"license": "mit"},
     "info": { /* any other model-info fields served verbatim: tags, downloads, likes, config, … */ },
     "files": {                             // path -> file; directories are implied by paths
       "README.md": {"text": "---\r\nlicense: mit\r\n---\r\n", "oid": "7be5fc7f…"},
       "big/pytorch_model.bin": {"size": 497807197, "oid": "…", "lfs": true}
     }}
  ],
  "requests": [
    {"repo": "Orosius/deltanet-mla-latent", "user": "TestingBOrig", "status": "pending",
     "timestamp": "2026-10-05T14:20:42.886Z", "reviewedAt": null, "grantedBy": null,
     "fields": null, "emailShared": true}
  ]
}
```

`emailShared: false` marks an entry created by **grant**, which the lists show without `email` (REQ-5).

Fields the clone added while implementing (part of the format, documented after the fact and
corrected by the clone builder):
- `users[].whoami`: extra `whoami-v2` fields served verbatim (`emailVerified`, `canPay`, `auth`, …).
- `repos[].dirs`: a **map** `{"<dir path>": {"oid": "…"}}` of recorded directory oids.
- `files[path]`: every key is optional (`text`, `oid`, `size`, `lfs`, `xetHash`). Missing values are
  synthesised from deterministic stub bytes: `oid` is the git blob sha1 of the bytes (or of the LFS
  pointer); above 8 MiB, a hash of a description is used instead.
- `files[path].lfs`: `true`, or an object with any subset of `{"oid": <sha256>, "size", "pointerSize"}`.
- `files[path].xetHash`: the xet hash, masked by ACC-9 for callers without access.

Built-in seeds:
- **`sandbox`** (the default): the real sandbox repo as recorded in
  `hf-gated/observations/2026-10-05-clone-seed-reads.json` (model info, tree, small file contents),
  the two users above, and `TestingBOrig` pending.
- Clone-only demo repos for gate-form coverage, all owned by `Orosius`:
  - `Orosius/gated-auto-demo`: auto, one checkbox field;
  - `Orosius/gated-form-demo`: manual, every field type, custom heading/description/button;
  - `Orosius/not-gated-demo`: `gated: false`, with a stale `extra_gated_description`.
- Third user `DemoCarol`, token `persona-carol`, with no relation to any repo (grant tests).
  **These demos and DemoCarol do not exist on huggingface.co.**
