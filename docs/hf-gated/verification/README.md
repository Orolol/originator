# Verification results

How we know the clone behaves like huggingface.co, from the strongest evidence to the weakest. Every
file here is generated; regenerate it rather than editing it.

| File | What it proves | How it was produced |
|---|---|---|
| [conformance-report.md](conformance-report.md) | The clone reproduces every recorded exchange with the real Hub: 8 scenarios, 292 recorded steps (283 replayed: 282 identical, 1 listed divergence; 9 outside the surface, skipped with a reason), each scenario from its recorded initial state. Only listed divergences remain (D-1 out of scope, D-4 unobserved docstring claim), and none is stale. | `conformance/` (blind suite: it never read the clone's code): `uv run --project conformance conformance-report --pytest` |
| [2026-10-05-clone-ui-walkthrough-vs-live.md](2026-10-05-clone-ui-walkthrough-vs-live.md) | The same scripted user journey through our web UI makes the clone fire **the same 13 state-changing requests** (bodies, statuses, responses) as the live session on huggingface.co, and the same multiset of reads. | `npm --prefix web run test:e2e:clone` + `harness/kb/compare_logs.py` |
| [conformance-live.md](conformance-live.md) | The recordings still describe today's Hub: 21 read-only steps replayed through the bridge, all matching. | `BACKEND_URL=http://127.0.0.1:8100 uv run --project conformance conformance-report --live` |

The pytest side of the suite adds rule tests by ID, the clone's provisional choices (a separate,
labelled group), and the official `huggingface_hub` client running its own access-request flow against
the clone: 304 passed, 1 strict expected failure (D-4) at the last run.

**What this does not prove.** HF's *own* web UI firing these requests, and its logged-in screens, have
not been recorded; that needs a browser session on huggingface.co. Behaviour listed in
[../open-questions.md](../open-questions.md) is provisional by definition: the clone's choice is
tested, not proven against the Hub.
