# Run: scripted UI walkthrough on the clone (2026-10-05)

- Agent type: general-purpose subagent, model **Sonnet** (bounded task with a recorded reference),
  background, in parallel with the blind conformance verifier (separate ports: clone 8201, web 3101).
- Ground truth: `docs/hf-gated/observations/2026-10-05-ui-walkthrough.json` (bridge log of the live
  walkthrough on huggingface.co).
- Output: `web/e2e/clone-walkthrough.spec.ts`, a clone-only Playwright config, and a log-diff tool.

## Prompt (verbatim)

You are adding a **scripted UI walkthrough** to `/home/orosius/workspace/originator` and running it against the **clone** (an in-memory replica of Hugging Face's gated-models backend). Goal: prove that the same scripted user journey, driven through our web UI, makes the clone fire the same requests and reach the same states as the real Hub did when a human did that journey live.

## Read first
1. `AGENTS.md` (hard rules), `docs/system.md` (personas, web conventions, clone control endpoints `/__clone__/state`, `/__clone__/log` — same entry schema as the bridge log).
2. `docs/hf-gated/ui.md` (screens A1–A6, B1–B3, C, side-effect matrix §D).
3. `web/README.md`, `web/playwright.config.ts`, `web/e2e/readonly.spec.ts` (existing read-only e2e against the live bridge — keep it untouched and keep its write-guard).
4. The ground truth: `docs/hf-gated/observations/2026-10-05-ui-walkthrough.json` — the bridge log of a live walkthrough a human did through this same web UI against the real huggingface.co (62 exchanges, 13 writes). Its steps, in order: requester (in `reset` state) opens `/Orosius/deltanet-mla-latent` and submits the consent form → owner opens `/Orosius/deltanet-mla-latent/settings`, opens "Review access requests", Accepts TestingBOrig → requester page shows no gate box and can download `.gitattributes` → owner Cancels (accepted tab) → owner Rejects (pending tab) → requester sees the rejected text → owner Accepts from the rejected tab → owner Cancels → owner sets "New requests" to Automatic approval then Manual review → Notifications frequency Real-time then Once a day → Disable Access requests → Enable Access requests → Manual review. Read the JSON to get the exact requests/bodies.

## Build
- `web/e2e/clone-walkthrough.spec.ts`: a Playwright test reproducing that journey **with role/label selectors only** (`getByRole('button', {name: 'Accept'})`, `getByRole('tab', {name: /accepted/})`, `getByLabel('New requests:')`…) — the same selectors should, in principle, work on huggingface.co. Persona switching via `/-/persona?as=…&next=…`. Before the journey: put the clone in the walkthrough's initial state (TestingBOrig's request on `Orosius/deltanet-mla-latent` in status `reset`; repo `gated: "manual"`) by `GET /__clone__/state` → modify → `PUT /__clone__/state`, then `DELETE /__clone__/log`. Assert the visible state after each step (texts from ui.md, tab counts, `Review access requests (N)`). Wait for the UI's refetch (it refetches lists ~1 s after an action) using Playwright auto-waiting on the expected text, not fixed sleeps where avoidable.
- A Playwright project/config for this run that targets the clone: run the clone on **port 8201** (`CLONE_PORT=8201 uv run --project clone clone`) and the web app on **port 3101** with `BACKEND_URL=http://127.0.0.1:8201` (production build + `next start`, like the existing e2e config does on 3100). You may add a second config file (e.g. `web/playwright.clone.config.ts`) and an npm script `test:e2e:clone`. Unlike the live-bridge e2e, writes are allowed here (the clone is local and in-memory) — but make the config refuse to run if `BACKEND_URL` is not a `127.0.0.1:82xx` clone (guard against hitting the bridge/live Hub).
- After the journey, fetch `GET /__clone__/log` and **diff it against the recorded live log**: a script (TypeScript in `web/e2e/` or Python in `harness/kb/`, your choice — if Python, put it at `harness/kb/compare_logs.py`, stdlib only, generic: two log files in the bridge-log schema → Markdown diff) that compares (1) the ordered sequence of **state-changing** requests: method, path, request body, response status, response body — must match exactly; (2) the GET/HEAD requests: compare as a multiset of (persona, method, path, status) — report differences (page loads may legitimately differ in count, e.g. retries/refetch timing; explain any). E-mails are redacted to `<email>` in the recording; normalise the clone's the same way. Timestamps are virtual-clock values on the clone — ignore `started_at`.
- Save the clone's log export with `python3 harness/kb/bridge_log_to_md.py` (it fetches `/__bridge__/log`; add a `--log-url` option to it, keeping the old default behaviour) into `web/e2e/out/` (gitignored), and the diff report into `web/e2e/out/clone-vs-live.md`. The orchestrator will publish it into docs.

## Constraints
- Do NOT use ports 8100 (bridge, live Hub — never send anything there), 8200 (another agent's clone), 3000 (a dev server may be running), 3100 is the read-only e2e's port. Use 8201 and 3101. Stop every server you start before finishing.
- Only modify `web/e2e/`, `web/playwright*.config.ts`, `web/package.json` (scripts), `web/.gitignore` (add `e2e/out/`), and `harness/kb/` (the log tools). Do not touch `clone/`, `conformance/`, `bridge/`, `docs/`, `writeup.md`, `AGENTS.md`, or the web app's `src/` — if the UI seems wrong, report it, don't fix it. No `git add`/`commit`. Never read `.env`.
- Playwright uses the system Chrome (`channel: "chrome"`), as the existing config does.
- Don't weaken assertions to pass; if the clone or UI diverges from the recorded live behaviour, report the exact divergence.

## Final report (short)
Commands to run; pass/fail of the walkthrough; the clone-vs-live diff summary (writes: N/13 identical; GETs: differences explained); any divergence found (verbatim), and whether it is in the UI or the clone.
