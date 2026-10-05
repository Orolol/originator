# Knowledge base

| Path | What | Kind |
|---|---|---|
| [assignement.md](assignement.md) | The take-home brief. **Read-only.** | input |
| [method.md](method.md) | How we replicate a slice: target-agnostic, reusable for the next slice or target | harness knowledge |
| [hf-gated/](hf-gated/README.md) | Everything about the current target slice (Hugging Face gated models) | target knowledge |

The project write-up is [../writeup.md](../writeup.md). It belongs to the candidate: **never edit it.**

## Evidence tags

Every non-obvious claim in a target KB carries a tag saying where it comes from. When sources
disagree, the higher one wins **and the conflict is written down** (in the rule or in
`open-questions.md`); it is never silently resolved.

| Tag | Meaning | Trust |
|---|---|---|
| `[OBS]` | Observed by us on the live target. Dated, reproducible by a checked-in script or recording. | 1 (highest) |
| `[CLIENT tests]` | Vendor's own integration tests that run against a real server instance | 2 |
| `[SPEC]` | Vendor-published machine-readable API spec (generated from server validators) | 3 |
| `[DOC]` | Vendor documentation prose. `[DOC-implied]`: a reasonable reading that the docs do not state. `[DOC-IMG]`: a doc screenshot (may be stale). | 4 |
| `[CLIENT]` / `[CLIENT doc]` | Vendor client source or docstrings (what the client *assumes* the server does) | 5 |
| `[JS]` | Other vendor client typings | 5 |
| `[OBS-3P]` | Third-party observation (error strings quoted in public issues); real but undated or unverifiable context | 6 |
| `[INFER]` / `[Q-n]` | Our inference, or an open question. Must not be implemented without a recorded provisional choice. | — |

## Conventions

- Rule IDs (`ACC-5`, `REV-4`…) are stable. Tests, commits and divergence notes cite them.
- Generated files (`observations/`, `snapshots/`) are never hand-edited; re-run the script.
- New finding → update the rule, tag it, and resolve or add the `Q-n` entry in the same change.
