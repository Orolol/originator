# Verification results

How we know the clone behaves like huggingface.co, from the strongest evidence to the weakest. Every
file here is generated; regenerate it rather than editing it.

| File | What it proves | How it was produced |
|---|---|---|
| [conformance-report.md](conformance-report.md) | The clone reproduces every recorded exchange with the real Hub, on **two sandboxes recorded on two days** (2026-10-05 `Orosius/deltanet-mla-latent`, 2026-10-06 `OwnerOfTheGatedModel/tiny-gated-model` with another owner account): 19 scenarios, 739 recorded steps (the 2026-10-06 set adds the requester self-cancel and an edge-case probe of the open questions), each scenario from its recorded initial state. Only listed divergences remain (D-1 out of scope, in both sets; D-5 a Hub lag, proven by a re-probe), and none is stale. | `conformance/` (blind suite: it never read the clone's code): `uv run --project conformance conformance-report --pytest` |
| [2026-10-06-clone-ui-walkthrough-vs-live.md](2026-10-06-clone-ui-walkthrough-vs-live.md) | **One Playwright script** (`web/e2e/walkthrough.ts`) drove our web UI against huggingface.co (through the bridge, twice) and against the clone: the clone fires **the same 15 state-changing requests** (bodies, statuses, responses), including the requester self-cancel, and the same multiset of 55 reads. | `E2E_LIVE_WRITES=1 npm --prefix web run test:e2e:live`, then `npm --prefix web run test:e2e:clone` + `harness/kb/compare_logs.py` |
| [2026-10-05-clone-ui-walkthrough-vs-live.md](2026-10-05-clone-ui-walkthrough-vs-live.md) | Earlier run: a journey done by hand through the UI on the first sandbox, scripted afterwards for the clone (13 writes identical). | the 2026-10-05 version of `test:e2e:clone` |
| [conformance-live.md](conformance-live.md) | The 2026-10-06 recordings still describe today's Hub: 21 read-only steps replayed through the bridge, all matching. | `BACKEND_URL=http://127.0.0.1:8100 uv run --project conformance conformance-report --live` |

The pytest side of the suite adds rule tests by ID, the clone's provisional choices (a separate,
labelled group), and the official `huggingface_hub` client running its own access-request flow against
the clone: 351 passed, no expected failure left (D-4 was settled by a recording) at the last run (2026-10-06).

**What this does not prove.** HF's *own* web UI firing these requests, and its logged-in screens, have
not been recorded; that needs a browser session on huggingface.co. Behaviour listed in
[../open-questions.md](../open-questions.md) is provisional by definition: the clone's choice is
tested, not proven against the Hub.
