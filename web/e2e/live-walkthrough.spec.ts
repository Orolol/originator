// Scripted UI walkthrough against the LIVE Hub through the bridge: the journey of `walkthrough.ts`,
// recorded as the ground truth the clone run is diffed against. It WRITES to huggingface.co (ask-access,
// self-cancel, handle, settings) on the sandbox repo only, and e-mails its owner (AGENTS.md "Live sandbox").
// Opt-in: `E2E_LIVE_WRITES=1 npm run test:e2e:live` (playwright.live.config.ts); the bridge must be
// running on :8100 with the tokens in `.env`.
//
// Before the journey the request is put in `reset` through the bridge (owner `handle`), the repo in
// "manual", then the bridge log is cleared. After it, the log is exported to
// docs/hf-gated/observations/<date>-ui-walkthrough.{json,md} by `harness/kb/bridge_log_to_md.py`.
import { spawnSync } from "node:child_process";
import path from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { REPO, REQUESTER, runJourney } from "./walkthrough";

const BRIDGE = "http://127.0.0.1:8100";
const OWNER = { Authorization: "Bearer persona-owner" };
const REQUESTER_AUTH = { Authorization: "Bearer persona-requester" };
const ROOT = path.resolve(__dirname, "..", "..");
const DATE = process.env.E2E_RECORDING_DATE ?? new Date().toISOString().slice(0, 10);
const OUT = `docs/hf-gated/observations/${DATE}-ui-walkthrough`;
const STATUSES = ["pending", "accepted", "rejected", "reset"] as const;

/** Current status of the requester's request, read from the four owner lists (none = no request). */
async function requestStatus(request: APIRequestContext): Promise<string | null> {
  for (const status of STATUSES) {
    const res = await request.get(`${BRIDGE}/api/models/${REPO}/user-access-request/${status}`, { headers: OWNER });
    expect(res.status(), `list ${status}`).toBe(200);
    const items: { user: { user: string } }[] = await res.json();
    if (items.some((item) => item.user.user === REQUESTER)) return status;
  }
  return null;
}

async function putInitialState(request: APIRequestContext) {
  const info = await request.get(`${BRIDGE}/api/models/${REPO}`, { headers: OWNER });
  expect(info.status()).toBe(200);
  if ((await info.json()).gated !== "manual") {
    const put = await request.put(`${BRIDGE}/api/models/${REPO}/settings`, { headers: OWNER, data: { gated: "manual" } });
    expect(put.status(), "PUT settings manual").toBe(200);
  }
  if ((await requestStatus(request)) === null) {
    const ask = await request.post(`${BRIDGE}/${REPO}/ask-access`, { headers: REQUESTER_AUTH, data: {}, maxRedirects: 0 });
    expect(ask.status(), "ask-access").toBe(303);
  }
  if ((await requestStatus(request)) !== "reset") {
    const reset = await request.post(`${BRIDGE}/api/models/${REPO}/user-access-request/handle`, {
      headers: OWNER,
      data: { user: REQUESTER, status: "reset", resetReason: "Reset before the scripted UI walkthrough" },
    });
    expect(reset.status(), "handle reset").toBe(200);
  }
  // Q-23: give the Hub a moment, then check the state the journey starts from.
  await expect.poll(() => requestStatus(request), { timeout: 15_000 }).toBe("reset");
  const cleared = await request.delete(`${BRIDGE}/__bridge__/log`);
  expect(cleared.ok(), "DELETE /__bridge__/log").toBe(true);
}

test("live: scripted UI walkthrough through the bridge (recording)", async ({ page, request }) => {
  expect(process.env.E2E_LIVE_WRITES, "set E2E_LIVE_WRITES=1: this run writes to huggingface.co").toBe("1");
  await putInitialState(request);
  try {
    await runJourney(page);
  } finally {
    // Export before the end-state check below, whose own reads must not land in the recording.
    const result = spawnSync(
      "python3",
      [
        "harness/kb/bridge_log_to_md.py",
        "--title", `Scripted UI walkthrough (Playwright, web/e2e/walkthrough.ts) through the bridge, ${DATE}`,
        "--out-json", `${OUT}.json`,
        "--out-md", `${OUT}.md`,
      ],
      { cwd: ROOT, encoding: "utf8" },
    );
    console.log(`${result.stdout}${result.stderr}`.trim());
  }
  await test.step("8. live state at the end: request pending, repo manual", async () => {
    await expect.poll(() => requestStatus(request), { timeout: 15_000 }).toBe("pending");
    const info = await request.get(`${BRIDGE}/api/models/${REPO}`, { headers: OWNER });
    expect((await info.json()).gated).toBe("manual");
  });
});
