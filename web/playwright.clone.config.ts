import { defineConfig } from "@playwright/test";
import { assertCloneBackendUrl } from "./e2e/cloneBackend";

// Scripted UI walkthrough against the CLONE (in-memory, local): writes are allowed here, unlike
// the read-only live-bridge e2e (`playwright.config.ts`). Starts its own clone on :8201 and the
// production web app on :3101 pointing at it (8100 = bridge/live Hub, 8200 = a clone others may use,
// 3000 = dev server, 3100 = the read-only e2e are left alone):
//   npm run test:e2e:clone
// The guard refuses any BACKEND_URL that is not http://127.0.0.1:82xx.
const BACKEND_URL = assertCloneBackendUrl(process.env.BACKEND_URL ?? "http://127.0.0.1:8201");
const WEB_PORT = Number(process.env.E2E_CLONE_WEB_PORT ?? 3101);
// The spec reads it back (workers inherit the environment) and applies the same guard.
process.env.BACKEND_URL = BACKEND_URL;

export default defineConfig({
  testDir: "e2e",
  testMatch: "clone-*.spec.ts",
  // One worker, no retries: the journey is a single stateful script, and a retry would replay writes.
  workers: 1,
  retries: 0,
  timeout: 240_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    // `localhost`, not 127.0.0.1, like the read-only e2e (Next refuses cross-site `/_next/*` loads from IP literals in dev).
    baseURL: `http://localhost:${WEB_PORT}`,
    // Playwright cannot install its bundled chromium on this host (Ubuntu 26.04): use system Chrome.
    channel: process.env.PLAYWRIGHT_CHANNEL ?? "chrome",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      // The clone is in memory and the spec resets its state, so reusing a running one is safe.
      command: "uv run --project clone clone",
      cwd: "..",
      env: { CLONE_PORT: new URL(BACKEND_URL).port },
      url: `${BACKEND_URL}/__clone__/health`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      // Never reuse: an already-running web app might point at another backend.
      command: `npm run build && npx next start -p ${WEB_PORT}`,
      env: { BACKEND_URL },
      url: `http://localhost:${WEB_PORT}/`,
      reuseExistingServer: false,
      timeout: 240_000,
    },
  ],
});
