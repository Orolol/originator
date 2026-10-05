// Scripted UI walkthrough against the CLONE: the journey a human did live through this same web UI
// against the real Hub (docs/hf-gated/observations/2026-10-05-ui-walkthrough.{json,md}), replayed
// step for step. Goal: the clone fires the same requests and reaches the same states.
//
//   1. requester (request in `reset`) submits the consent form
//   2. owner: Review access requests → Accept            3. requester: no gate box, opens .gitattributes
//   4. owner: Cancel (accepted tab), then Reject (pending tab)
//   5. requester: sees the rejected text
//   6. owner: Accept (rejected tab), then Cancel (accepted tab)
//   7. owner: New requests Automatic → Manual, Notifications frequency Real-time → Once a day,
//      Disable Access requests → Enable Access requests → Manual review, reload
//
// Selectors are roles and labels only, so the same script should in principle run on huggingface.co.
// At the end the clone's exchange log is exported to `e2e/out/` and diffed against the live recording
// by `harness/kb/compare_logs.py` (state-changing requests must match exactly).
// Run with `npm run test:e2e:clone` (playwright.clone.config.ts); it refuses any non-clone backend.
import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { assertCloneBackendUrl } from "./cloneBackend";

const BACKEND = assertCloneBackendUrl(process.env.BACKEND_URL);
const REPO = "Orosius/deltanet-mla-latent";
const REQUESTER = "TestingBOrig";

const DEFAULT_HEADING = "You need to agree to share your contact information to access this model";
const SUBMIT = "Agree and send request to access repo";
const AWAITING = `Your request to access model ${REPO} is awaiting a review from the repo authors.`;
const REJECTED = "Your request to access this repo has been rejected by the repo's authors.";
const ENABLED = "Access requests are currently enabled for this model.";
const DISABLED = "Access requests are currently disabled for this model.";
const GITATTRIBUTES_FIRST_LINE = "*.7z filter=lfs diff=lfs merge=lfs -text";

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(__dirname, "out");
const rel = (file: string) => path.relative(ROOT, file);
const LIVE_LOG = "docs/hf-gated/observations/2026-10-05-ui-walkthrough.json";
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

// ---------------------------------------------------------------- UI helpers (roles and labels only)

/** Persona switch (`/-/persona?as=…&next=…`), then wait for the page to settle (hydration) before clicking. */
async function actAs(page: Page, persona: "requester" | "owner", pathname: string) {
  await page.goto(`/-/persona?as=${persona}&next=${encodeURIComponent(pathname)}`);
  await expect(page).toHaveURL((url) => url.pathname === pathname);
  await page.waitForLoadState("networkidle");
}

const reviewButton = (page: Page, pending: number) =>
  page.getByRole("button", { name: `Review access requests (${pending})`, exact: true });
const manageDialog = (page: Page) => page.getByRole("dialog", { name: "Manage access requests" });
const tabOf = (dialog: Locator, status: string, count: number) =>
  dialog.getByRole("tab", { name: `${status} (${count})`, exact: true });
const rowOf = (dialog: Locator, user: string) =>
  dialog.getByRole("listitem").filter({ has: dialog.page().getByRole("link", { name: user, exact: true }) });

/** Tab counts after the UI's refetch (~1 s after an action): auto-waits on the expected labels. */
async function expectCounts(dialog: Locator, counts: { pending: number; accepted: number; rejected: number }) {
  for (const [status, count] of Object.entries(counts)) await expect(tabOf(dialog, status, count)).toBeVisible();
}

/** Runs `action` and checks the browser fired exactly this write (method, path, JSON body) and got 200. */
async function fires(page: Page, method: "POST" | "PUT", suffix: string, body: unknown, action: () => Promise<unknown>) {
  const [response] = await Promise.all([
    page.waitForResponse((r) => r.request().method() === method && new URL(r.url()).pathname === `/api/models/${REPO}${suffix}`),
    action(),
  ]);
  expect(response.status(), `${method} ${suffix}`).toBe(200);
  expect(response.request().postDataJSON()).toEqual(body);
}

const handle = (page: Page, status: string, action: () => Promise<unknown>) =>
  fires(page, "POST", "/user-access-request/handle", { user: REQUESTER, status }, action);
const putSettings = (page: Page, body: Record<string, unknown>, action: () => Promise<unknown>) =>
  fires(page, "PUT", "/settings", body, action);

async function openReviewModal(page: Page, pending: number) {
  await reviewButton(page, pending).click();
  const dialog = manageDialog(page);
  await expect(dialog).toBeVisible();
  return dialog;
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
    await test.step("1. requester (request reset) opens the repo page and submits the consent form", async () => {
      await actAs(page, "requester", `/${REPO}`);
      // A6 (ui.md): after a reset the consent form is shown again.
      await expect(page.getByRole("heading", { name: DEFAULT_HEADING })).toBeVisible();
      await expect(
        page.getByText("By agreeing you accept to share your contact information (email and username) with the repository authors."),
      ).toBeVisible();
      await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
      await page.getByRole("button", { name: SUBMIT }).click();
      // ask-access → 303 → repo page, now pending (A3).
      await expect(page.getByText(AWAITING)).toBeVisible();
      await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
    });

    await test.step("2. owner opens Review access requests (1) and accepts TestingBOrig", async () => {
      await actAs(page, "owner", `/${REPO}/settings`);
      await expect(page.getByText(ENABLED)).toBeVisible();
      await expect(page.getByLabel("New requests:")).toHaveValue("manual");
      const dialog = await openReviewModal(page, 1);
      await expectCounts(dialog, { pending: 1, accepted: 0, rejected: 0 });
      await expect(tabOf(dialog, "pending", 1)).toHaveAttribute("aria-selected", "true");
      const row = rowOf(dialog, REQUESTER);
      await expect(row.getByRole("button", { name: "Accept" })).toBeVisible();
      await expect(row.getByRole("button", { name: "Reject" })).toBeVisible();
      await handle(page, "accepted", () => row.getByRole("button", { name: "Accept" }).click());
      // The UI refetches the three lists ~1 s later: the row leaves the pending tab, N drops to 0.
      await expectCounts(dialog, { pending: 0, accepted: 1, rejected: 0 });
      await expect(dialog.getByRole("listitem")).toHaveCount(0);
      await expect(reviewButton(page, 0)).toBeVisible();
    });

    await test.step("3. requester: no gate box any more, downloads .gitattributes", async () => {
      await actAs(page, "requester", `/${REPO}`);
      await expect(page.getByRole("link", { name: ".gitattributes", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: DEFAULT_HEADING })).toHaveCount(0);
      await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
      await expect(page.getByText(AWAITING)).toHaveCount(0);
      const [file] = await Promise.all([
        page.waitForResponse((r) => new URL(r.url()).pathname === `/${REPO}/resolve/main/.gitattributes`),
        page.getByRole("link", { name: ".gitattributes", exact: true }).click(),
      ]);
      expect(file.status()).toBe(200);
      await expect(page.getByText(GITATTRIBUTES_FIRST_LINE)).toBeVisible();
    });

    await test.step("4. owner cancels (accepted tab), then rejects (pending tab)", async () => {
      await actAs(page, "owner", `/${REPO}/settings`);
      const dialog = await openReviewModal(page, 0);
      await expectCounts(dialog, { pending: 0, accepted: 1, rejected: 0 });
      await tabOf(dialog, "accepted", 1).click();
      await expect(tabOf(dialog, "accepted", 1)).toHaveAttribute("aria-selected", "true");
      const acceptedRow = rowOf(dialog, REQUESTER);
      await expect(acceptedRow.getByRole("button", { name: "Reject" })).toBeVisible();
      await expect(acceptedRow.getByRole("button", { name: "Accept" })).toHaveCount(0);
      await handle(page, "pending", () => acceptedRow.getByRole("button", { name: "Cancel" }).click());
      await expectCounts(dialog, { pending: 1, accepted: 0, rejected: 0 });
      await expect(dialog.getByRole("listitem")).toHaveCount(0); // still on the (now empty) accepted tab

      await tabOf(dialog, "pending", 1).click();
      await expect(tabOf(dialog, "pending", 1)).toHaveAttribute("aria-selected", "true");
      const pendingRow = rowOf(dialog, REQUESTER);
      await handle(page, "rejected", () => pendingRow.getByRole("button", { name: "Reject" }).click());
      await expectCounts(dialog, { pending: 0, accepted: 0, rejected: 1 });
      await expect(reviewButton(page, 0)).toBeVisible();
    });

    await test.step("5. requester sees the rejected text and no form", async () => {
      await actAs(page, "requester", `/${REPO}`);
      await expect(page.getByText(REJECTED)).toBeVisible();
      await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
      await expect(page.getByText(AWAITING)).toHaveCount(0);
    });

    await test.step("6. owner accepts from the rejected tab, then cancels (accepted tab)", async () => {
      await actAs(page, "owner", `/${REPO}/settings`);
      const dialog = await openReviewModal(page, 0);
      await expectCounts(dialog, { pending: 0, accepted: 0, rejected: 1 });
      await tabOf(dialog, "rejected", 1).click();
      await expect(tabOf(dialog, "rejected", 1)).toHaveAttribute("aria-selected", "true");
      const rejectedRow = rowOf(dialog, REQUESTER);
      await expect(rejectedRow.getByRole("button", { name: "Cancel" })).toBeVisible();
      await handle(page, "accepted", () => rejectedRow.getByRole("button", { name: "Accept" }).click());
      await expectCounts(dialog, { pending: 0, accepted: 1, rejected: 0 });

      await tabOf(dialog, "accepted", 1).click();
      await expect(tabOf(dialog, "accepted", 1)).toHaveAttribute("aria-selected", "true");
      const acceptedRow = rowOf(dialog, REQUESTER);
      await handle(page, "pending", () => acceptedRow.getByRole("button", { name: "Cancel" }).click());
      await expectCounts(dialog, { pending: 1, accepted: 0, rejected: 0 });
      await expect(reviewButton(page, 1)).toBeVisible();
      await dialog.getByRole("button", { name: "Close" }).click();
      await expect(dialog).toHaveCount(0);
    });

    await test.step("7. owner settings: New requests, Notifications frequency, Disable / Enable", async () => {
      const newRequests = page.getByLabel("New requests:");
      const frequency = page.getByLabel("Notifications frequency");
      const addAccess = page.getByRole("button", { name: "Add access" });

      await putSettings(page, { gated: "auto" }, () => newRequests.selectOption({ label: "Automatic approval" }));
      await expect(newRequests).toHaveValue("auto");
      // B2: automatic approval has no Add access and no notifications row.
      await expect(addAccess).toHaveCount(0);
      await expect(frequency).toHaveCount(0);

      await putSettings(page, { gated: "manual" }, () => newRequests.selectOption({ label: "Manual review" }));
      await expect(newRequests).toHaveValue("manual");
      await expect(addAccess).toBeVisible();
      await expect(frequency).toHaveValue("bulk");

      await putSettings(page, { gatedNotificationsMode: "real-time" }, () => frequency.selectOption({ label: "Real-time" }));
      await expect(frequency).toHaveValue("real-time");
      await putSettings(page, { gatedNotificationsMode: "bulk" }, () => frequency.selectOption({ label: "Once a day" }));
      await expect(frequency).toHaveValue("bulk");

      await putSettings(page, { gated: false }, () => page.getByRole("button", { name: "Disable Access requests" }).click());
      await expect(page.getByText(DISABLED)).toBeVisible(); // B1
      await expect(page.getByRole("button", { name: "Enable Access requests" })).toBeVisible();
      await expect(newRequests).toHaveCount(0);
      await expect(page.getByRole("button", { name: /^Review access requests/ })).toHaveCount(0);

      await putSettings(page, { gated: "auto" }, () => page.getByRole("button", { name: "Enable Access requests" }).click());
      await expect(page.getByText(ENABLED)).toBeVisible();
      await expect(newRequests).toHaveValue("auto"); // CFG-1: enabling starts in automatic approval

      await putSettings(page, { gated: "manual" }, () => newRequests.selectOption({ label: "Manual review" }));
      await expect(newRequests).toHaveValue("manual");
      await expect(addAccess).toBeVisible();

      // A reload shows what the backend kept (the live walkthrough ended the same way).
      await page.reload();
      await page.waitForLoadState("networkidle");
      await expect(page.getByText(ENABLED)).toBeVisible();
      await expect(newRequests).toHaveValue("manual");
      await expect(reviewButton(page, 1)).toBeVisible();
    });

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
