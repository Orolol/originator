import { defineConfig } from "@playwright/test";

// Scripted UI walkthrough against the LIVE Hub through the bridge (it WRITES on the sandbox repo):
//   E2E_LIVE_WRITES=1 npm run test:e2e:live
// The bridge must already run on :8100. The web app is a production build on :3102 pinned to it.
const WEB_PORT = Number(process.env.E2E_LIVE_WEB_PORT ?? 3102);
const BACKEND_URL = "http://127.0.0.1:8100";

if (process.env.E2E_LIVE_WRITES !== "1") {
  throw new Error("Refusing to run the live walkthrough: it writes to huggingface.co. Set E2E_LIVE_WRITES=1.");
}

export default defineConfig({
  testDir: "e2e",
  testMatch: "live-*.spec.ts",
  // One worker, no retries: a retry would replay writes on the real Hub.
  workers: 1,
  retries: 0,
  timeout: 300_000,
  // The real Hub is slower than the clone and eventually consistent (Q-23).
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    channel: process.env.PLAYWRIGHT_CHANNEL ?? "chrome",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run build && npx next start -p ${WEB_PORT}`,
    env: { BACKEND_URL },
    url: `http://localhost:${WEB_PORT}/`,
    reuseExistingServer: false,
    timeout: 240_000,
  },
});
