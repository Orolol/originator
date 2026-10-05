# Replication method (target-agnostic)

How this repo takes a slice of a closed-source product from "unknown" to "verified clone". Nothing
here is specific to Hugging Face; the target-specific knowledge lives in `docs/<target>/`. This
file is the part of the harness meant to make the *next* slice faster than the first.

## 1. The loop

| Phase | Output | Done when |
|---|---|---|
| 1. Scope | `docs/<target>/README.md`: slice, actors, glossary, MVP vs out | one workflow end to end is named; adjacent features are listed as out |
| 2. Gather | tagged claims from every free source: docs source, published API spec, open-source clients **and their integration tests**, read-only live probes | each source pinned in `sources.md` |
| 3. Specify | `behaviour.md` (rules with IDs), `api.md` (wire protocol), `ui.md` (screens and side effects), `open-questions.md` | every rule has an evidence tag; every unknown is a `Q-n` with a priority |
| 4. Record | fixtures from the real target: anonymous probes first, then stateful sessions on sandbox resources (through the bridge) | P0 questions answered with `[OBS]` |
| 5. Build | clone (backend + screens), behind the same protocol as the target | conformance scenarios pass against the clone |
| 6. Verify | the same scenario scripts run against the target (through the bridge) and the clone; diff the normalised outputs | divergences are either fixed or written up as gaps, by rule ID |

Phases 3–6 iterate: a divergence found in phase 6 is new evidence, so update the rule and the
question and re-run.

## 2. Principles

1. **Evidence over plausibility.** Every implemented behaviour traces to a tagged rule. LLM recall
   ("I think HF returns 403 here") is `[INFER]` until observed. When a source is silent, write
   `Q-n` rather than invent.
2. **Mine the vendor's tests.** Open-source clients often ship integration tests that run against
   a real server. They are recorded behaviour, ranked above the prose docs.
3. **Speak the target's protocol.** The clone exposes the same paths, payloads, status codes and
   error headers. Then the vendor's own client, our bridge and our scripts drive both sides
   unchanged, and "same script, two backends" becomes the test.
4. **Bridge first, then replace.** The UI is built against a thin bridge to the real backend, so
   UI behaviour is validated by the real thing; then the backend is swapped for the clone. The UI
   never knows which one it talks to (`BACKEND_URL`).
5. **Determinism is designed in.** In-memory state only; seed fixtures at start; a reset call
   restores them; an injectable clock; sequential IDs; stable ordering; side effects we cannot
   reproduce (emails) go to an inspectable outbox.
6. **Read-only by default on the real target.** Anonymous `GET`/`HEAD` probes are scripted
   (`harness/kb/probe.py`). State-changing calls happen only through the bridge, only on sandbox
   resources owned by our own accounts, and are recorded.
7. **Honest gaps.** A test is never weakened to pass. A known divergence is listed with its rule
   ID, the evidence, and why it is not fixed.

## 3. Normalising recordings for diffs

When comparing target and clone outputs, normalise only what is legitimately volatile, and list
each normalisation in the target KB: timestamps → relative order or `<ts>`, ObjectIds → stable
aliases, avatar URLs, request IDs, CDN headers. Everything else (status codes, `X-Error-*`
headers, field presence, list order, messages) must match exactly.

## 4. Agents

Model choice follows the global rules: Fable for design, arbitration and final review; Opus for
hard implementation; Sonnet for bounded tasks and repeated critique; Haiku for chores.

| Role | Input | Output | Must not |
|---|---|---|---|
| Researcher | sources, probe cases | tagged claims, observations | implement |
| Spec writer | claims | rules with IDs, open questions | resolve a conflict silently |
| Implementer | `behaviour.md`, `api.md`, `ui.md` | clone code citing rule IDs | add behaviour without a rule or recorded provisional choice |
| Verifier | **spec only, not the implementation** | conformance scenarios per rule ID | read the clone's code to decide expected values |
| Reviewer | diff, failing scenarios | divergence notes, fix requests | relax tests |

Keeping the verifier blind to the implementation is what stops the LLM from writing tests that
merely agree with its own code.

## 5. Starting a new slice or target

1. Create `docs/<target>/` with the same files: `README.md`, `behaviour.md`, `api.md`, `ui.md`,
   `open-questions.md`, `sources.md`, `out-of-scope.md`, `observations/`, `snapshots/`.
2. Pin the sources (clone docs and clients into a scratch dir, never into the repo).
3. If the vendor publishes an API spec, extract the slice with `harness/kb/extract_openapi.py`.
4. Write read-only probe cases in `harness/kb/probes/<target>-*.json`, run `harness/kb/probe.py`,
   and commit the generated observation.
5. Write the rules, then the questions, then record against the target to close the P0s.
