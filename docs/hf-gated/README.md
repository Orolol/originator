# Target: Hugging Face Hub, slice: gated models

**Target.** huggingface.co (closed-source server). The open-source clients
(`huggingface_hub`, `huggingface.js`), the docs source and the published OpenAPI spec make it
unusually cross-checkable.

**Slice.** The access-request lifecycle of a gated model: the owner turns gating on and picks automatic
or manual approval; a requester agrees to share their details through a configurable form; the owner
reviews (accept / reject with reason / cancel / reset / grant / batch); and the resulting
**authorisation decision** on file downloads, with its exact error semantics. It has states,
branching on mode and status, error ordering, and observable side effects (redirects, error headers,
report export, emails). Rationale and approach choice: [../../writeup.md](../../writeup.md).

## Reading order

1. [behaviour.md](behaviour.md): **the spec**. Entities, states, transition tables, access rules
   (rule IDs `CFG-*`, `ACC-*`, `REQ-*`, `REV-*`, `TS-*`, `REP-*`).
2. [api.md](api.md): the wire protocol the clone must speak (paths, payloads, status codes,
   `X-Error-*` headers, client gotchas).
3. [ui.md](ui.md): screens and states for requester and owner, the side-effect matrix and the
   recording checklist.
4. [gate-form.md](gate-form.md): `extra_gated_*` card metadata → consent form; live examples
   that make good seed fixtures.
5. [open-questions.md](open-questions.md): everything not yet verified (Q-1…Q-24), by priority.
6. [client-library.md](client-library.md): what `huggingface_hub` covers, its documented errors,
   and its integration tests as recorded behaviour.
7. [out-of-scope.md](out-of-scope.md): adjacent features deliberately excluded, and why.
8. [sources.md](sources.md): pinned sources and how to re-fetch them.
9. `observations/`: raw recorded probes (generated; do not hand-edit). `snapshots/`: generated
   extracts of the vendor spec.
10. [verification/](verification/README.md): what is proven about the clone (conformance report,
    clone-vs-live UI walkthrough diff, live re-check), and what is not.

## Scope

**MVP (must be faithful and verified):**
- repo gating config: `gated` false/auto/manual (settings API + settings section);
- the gate form rendered from seeded `cardData` (all field types);
- requester flow: anonymous view, logged-in form, submit, status per state;
- owner review: four lists, handle (accept / reject+reason / cancel / reset), grant, batch;
- the authorisation decision on `resolve` / `auth-check`: allowlist, gate-before-existence, 401 vs
  403, `X-Error-Code`;
- the access report download.

**Next, if time allows:** notification settings (stored, outbox only), `orgMembersGated`,
requester self-cancel (depends on Q-3), exact search and pagination semantics.

**Out:** see [out-of-scope.md](out-of-scope.md).

## Actors

| Actor | Can |
|---|---|
| Anonymous visitor | see the page, metadata, file list, gate box (no form); download only allowlisted files |
| Logged-in requester | submit the gate form once (unless reset); read files when accepted |
| Repo owner (user namespace) or org member with write/admin | configure gating, review requests, grant, download the report; always reads files |
| Org member (read role) | bypasses the gate unless `orgMembersGated` |

## Glossary

- **Gated repo / access requests enabled**: `gated != false`. The repo stays *public* (page,
  metadata and file list visible), but file contents require an accepted request.
- **Automatic approval** (`auto`) / **Manual review** (`manual`): whether a new request lands in
  `accepted` or `pending`.
- **Handle**: the owner sets a request's status. UI verbs: *Accept* → accepted, *Reject* →
  rejected, *Cancel* → pending (the client's `cancel_access_request` means this too), *Reset* → reset.
- **Grant / Add access**: put a user in `accepted` without a request from them.
- **Reset**: revoke and ask the user to agree again (email sent). Unlike *rejected*, the user may request again.
- **Gate form / consent form**: what the requester fills, configured by `extra_gated_*` YAML.
- **Allowlist**: root `README.md`, `LICENSE`, `LICENSE.md`, `LICENSE.txt`, downloadable through
  `resolve` without access.
- **Access report**: owner's export of all requests ("Download user access report").
