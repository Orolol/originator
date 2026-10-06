// Scripted UI walkthrough against the CLONE: the journey of `walkthrough.ts`, which the live run
// (`live-walkthrough.spec.ts`) drove through the bridge against the real Hub
// (docs/hf-gated/observations/2026-10-06-ui-walkthrough.{json,md}). Goal: the clone fires the same
// requests and reaches the same states. At the end the clone's exchange log is exported to `e2e/out/`
// and diffed against the live recording by `harness/kb/compare_logs.py` (state-changing requests must
// match exactly).
// Run with `npm run test:e2e:clone` (playwright.clone.config.ts); it refuses any non-clone backend.
import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { assertCloneBackendUrl } from "./cloneBackend";
import { REPO, REQUESTER, runJourney } from "./walkthrough";

const BACKEND = assertCloneBackendUrl(process.env.BACKEND_URL);
const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(__dirname, "out");
const rel = (file: string) => path.relative(ROOT, file);
const LIVE_LOG = "docs/hf-gated/observations/2026-10-06-ui-walkthrough.json";
const CLONE_LOG_JSON = rel(path.join(OUT, "clone-ui-walkthrough.json"));
const CLONE_LOG_MD = rel(path.join(OUT, "clone-ui-walkthrough.md"));
const DIFF_MD = rel(path.join(OUT, "clone-vs-live.md"));

// ---------------------------------------------------------------- clone control (not part of HF's surface)

async function cloneJson(request: APIRequestContext, method: "get" | "put" | "delete", pathname: string, data?: unknown) {
  const response = await request[method](`${BACKEND}${pathname}`, data === undefined ? {} : { data });
  expect(response.ok(), `${method.toUpperCase()} ${pathname}: HTTP ${response.status()}`).toBe(true);
  return response.json();
}

/** Refuses anything that does not answer like the clone (the bridge has no `/__clone__/` routes). */
async function assertIsClone(request: APIRequestContext) {
  const health = await request.get(`${BACKEND}/__clone__/health`).catch(() => null);
  const body = health?.ok() ? await health.json().catch(() => null) : null;
  expect(body?.ok === true && typeof body?.seed === "string", `${BACKEND} is not a clone (/__clone__/health)`).toBe(true);
}

/**
 * The walkthrough's initial state: TestingBOrig's request on the sandbox repo in status `reset`,
 * the repo gated "manual" (default notifications), then an empty log. Reset to the `sandbox` seed
 * first (it holds TestingBOrig's recorded request; the default `clean` seed has none) so a reused
 * clone starts from the seed's clock and ids too.
 */
async function putInitialState(request: APIRequestContext) {
  const reset = await request.post(`${BACKEND}/__clone__/reset`, { data: { seed: "sandbox" } });
  expect(reset.ok(), "POST /__clone__/reset").toBe(true);
  const state = await cloneJson(request, "get", "/__clone__/state");
  const repo = state.repos.find((r: { id: string }) => r.id === REPO);
  expect(repo, `repo ${REPO} in the clone state`).toBeTruthy();
  repo.gated = "manual";
  repo.gatedNotificationsMode = "bulk";
  repo.gatedNotificationsEmail = null;
  const entry = state.requests.find((r: { repo: string; user: string }) => r.repo === REPO && r.user === REQUESTER);
  expect(entry, `request of ${REQUESTER} in the seed`).toBeTruthy();
  Object.assign(entry, { status: "reset", reviewedAt: state.now, grantedBy: null });
  await cloneJson(request, "put", "/__clone__/state", state);
  await cloneJson(request, "delete", "/__clone__/log");
  const log = await cloneJson(request, "get", "/__clone__/log");
  expect(log, "log is empty before the journey").toEqual([]);
}

// ---------------------------------------------------------------- log export and diff

/** Runs a `harness/kb` tool from the repo root; file arguments are relative to it (they end up in the report). */
function python(script: string, args: string[]) {
  const result = spawnSync("python3", [path.join("harness/kb", script), ...args], { cwd: ROOT, encoding: "utf8" });
  return { status: result.status, output: `${result.stdout}${result.stderr}`.trim() };
}

function exportCloneLog() {
  mkdirSync(OUT, { recursive: true });
  return python("bridge_log_to_md.py", [
    "--log-url", `${BACKEND}/__clone__/log`,
    "--title", "Scripted UI walkthrough (Playwright) against the clone",
    "--out-json", CLONE_LOG_JSON,
    "--out-md", CLONE_LOG_MD,
  ]);
}

// ---------------------------------------------------------------- the journey

test("clone: scripted UI walkthrough fires the live Hub's requests and reaches its states", async ({ page, request }) => {
  await assertIsClone(request);
  await putInitialState(request);

  try {
    await runJourney(page);

    await test.step("8. clone state at the end: request pending, repo manual, default notifications", async () => {
      const state = await cloneJson(request, "get", "/__clone__/state");
      const entry = state.requests.find((r: { repo: string; user: string }) => r.repo === REPO && r.user === REQUESTER);
      expect(entry.status).toBe("pending");
      const repo = state.repos.find((r: { id: string }) => r.id === REPO);
      expect(repo.gated).toBe("manual");
      expect(repo.gatedNotificationsMode).toBe("bulk");
    });
  } finally {
    // Keep the clone's log even when a step failed (best effort), to diagnose from it.
    const exported = exportCloneLog();
    if (exported.status !== 0) console.error(`log export failed:\n${exported.output}`);
  }

  await test.step("9. clone log vs the live recording: state-changing requests identical", async () => {
    const diff = python("compare_logs.py", [LIVE_LOG, CLONE_LOG_JSON, "--out-md", DIFF_MD]);
    console.log(`${diff.output}\nreport: ${DIFF_MD}`);
    expect(diff.status, `compare_logs.py (report: ${DIFF_MD})\n${diff.output}`).toBe(0);
  });
});
