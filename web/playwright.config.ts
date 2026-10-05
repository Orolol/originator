import { defineConfig } from "@playwright/test";

// Read-only e2e against a live backend (bridge by default, BACKEND_URL otherwise).
// Start the bridge first: `uv run --project bridge bridge` from the repo root.
const PORT = Number(process.env.E2E_PORT ?? 3100);

export default defineConfig({
  testDir: "e2e",
  // One worker: the live Hub is shared state and rate-limited.
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    // `localhost`, not 127.0.0.1: Next 16 refuses cross-site `/_next/*` loads from IP literals in dev.
    baseURL: `http://localhost:${PORT}`,
    // Playwright cannot install its bundled chromium on this host (Ubuntu 26.04): use system Chrome.
    // PLAYWRIGHT_CHANNEL= (empty) selects the bundled browser where it is installed.
    channel: process.env.PLAYWRIGHT_CHANNEL ?? "chrome",
  },
  webServer: {
    command: `npm run build && npx next start -p ${PORT}`,
    url: `http://localhost:${PORT}/`,
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
