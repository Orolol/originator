# Adjacent features: known, deliberately out of the slice

Listed so that nobody "discovers" them mid-implementation and widens the scope. Each could be a
second slice; the reason it is out is given.

| Feature | What we know | Why it is out |
|---|---|---|
| **Gated datasets** | Same API under `/api/datasets/…` and `/datasets/{ns}/{repo}/…`; the docs page is a near copy of the models one. [DOC] [SPEC] | Pure parity, no new logic. The cheapest "second slice" for proving the harness: parametrise `repo_type`. |
| **Spaces / kernels** | The spaces settings schema accepts `gated`; kernels have `gated` plus a separate `POST /api/kernels/access-request/approve`. [SPEC] | Not documented as a user feature for Spaces; kernels have a different flow. |
| **Gating Group Collections** (Team/Enterprise) | Org collection with `gating: false \| {mode:"auto"} \| {mode:"manual", notifications:{mode, email?}}`. Approving a request on any repo approves **all** repos in the collection, including future ones. A repo belongs to at most one gating group, and all repos must belong to the collection's org. Gate form metadata stays per-repo, with no central config. [DOC] [SPEC] | Needs orgs, collections and paid plans; it multiplies state. |
| **Org-member gating** (`orgMembersGated`) | Members must request; org admins, the repo creator and Resource Group admins bypass. [DOC] [SPEC] | Needs an org/role model. Candidate for "later" in the slice (one flag, small rule). |
| **EU restriction** (`extra_gated_eu_disallowed`) | IP-based; only active when the repo is gated. [DOC] | Geolocation is not reproducible deterministically, except by injecting the country. |
| **Advanced Gating** (Enterprise Plus) | Blocked countries/regions; enforcement "gated repos" (auto-reject) or "all repos" (deny downloads, region notice). [DOC] | Paid tier, geolocation. |
| **Emails / notifications** | Manual-mode notifications (real-time or daily), reset email, user preference `gated_user_access_request`. [DOC] [SPEC] | Not observable by a test harness; the clone records an outbox instead. |
| **Token scopes** | Fine-grained `canReadGatedRepos`; OAuth / CI-identity `gated-repos` scope reads public gated repos the user was granted. [SPEC] [DOC] | Auth system, not gating logic. The clone uses plain seeded tokens. |
| **`requiresPaidPlan`, `isGoogleGemma`** | Gate-component props observed on the page. [OBS] | Vendor-specific special cases. |
| **Inference / widgets on gated models** | | Unrelated product surface. |
| **Editing the gate form** | It is a commit to `README.md` YAML. | Commit API is a different slice; the clone seeds `cardData`. |
| **Real file serving** (LFS/Xet, 302 to CDN) | | The clone serves stub bytes for allowlisted or authorised files; only the authorisation decision is in slice. |
| **Rate limits** | All API calls are rate-limited. [DOC] | Not business logic. |
