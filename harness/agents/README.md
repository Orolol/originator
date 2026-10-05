# Agent prompts

Prompts actually given to subagents, checked in verbatim so the run can be audited and replayed.

| File | Role | Model | Why that model |
|---|---|---|---|
| [runs/2026-10-05-bridge-builder.md](runs/2026-10-05-bridge-builder.md) | Build the Python bridge (HF-compatible proxy with personas, allowlists, exchange log) | Sonnet | Fully specified by `docs/system.md`; bounded |
| [runs/2026-10-05-ui-builder.md](runs/2026-10-05-ui-builder.md) | Build the Next.js UI (gate box, settings section, review modal) | Opus | Several screens and states, many provisional decisions to flag |
| [runs/2026-10-05-clone-builder.md](runs/2026-10-05-clone-builder.md) | Build the in-memory clone (state machine, wire protocol, seeds, control endpoints) | Opus | Core business logic; fidelity-critical |
| [runs/2026-10-05-conformance-verifier.md](runs/2026-10-05-conformance-verifier.md) | Build the **blind** conformance suite (fixture replay, rule tests, official client driver) | Opus | Verification quality is the grading criterion; must judge normalisations |

Each pair ran **in parallel** against a contract written first ([docs/system.md](../../docs/system.md)):
bridge + UI, then clone + verifier. The verifier may not read the clone's code (only its README and
pyproject), so its tests come from the spec and the recordings, never from the implementation.

## Patterns these prompts share (reuse them for the next slice)

1. **Mandatory reading list, in order.** Hard rules → contract → spec → open questions. The agent
   learns what is *unknown* before it starts coding.
2. **Unknowns are flagged, not invented.** Any behaviour not backed by the KB is marked
   `Provisional (Q-n)` in code and listed in the final report. The orchestrator, not the agent,
   writes it into `open-questions.md`, so parallel agents never edit the KB concurrently.
3. **Side-effect fence.** Subagents may only *read* the live target. State-changing calls are
   reserved for the orchestrator, who runs them deliberately and records them.
4. **File-ownership fence.** Each agent owns one directory, and nobody commits but the orchestrator.
5. **Secrets fence.** Tokens stay in `.env`, which agents never print, and persona tokens are fake.
6. **Definition of done** is executable: tests pass offline, live read-only smoke passes, the
   server starts.
7. **Short structured final report.** It covers what was built, how to run it, test counts,
   deviations and provisional choices.
