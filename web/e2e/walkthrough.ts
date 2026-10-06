// The scripted UI walkthrough, shared by the clone run (`clone-walkthrough.spec.ts`) and the live run
// through the bridge (`live-walkthrough.spec.ts`): the SAME journey drives both backends, and the
// clone's exchange log is diffed against the bridge log of the live run.
//
//   1. requester (request in `reset`) submits the consent form
//   1b. requester cancels the pending request (self-cancel, Q-3) and submits it again
//   2. owner: Review access requests → Accept            3. requester: no gate box, opens .gitattributes
//   4. owner: Cancel (accepted tab), then Reject (pending tab)
//   5. requester: sees the rejected text
//   6. owner: Accept (rejected tab), then Cancel (accepted tab)
//   7. owner: New requests Automatic → Manual, Notifications frequency Real-time → Once a day,
//      Disable Access requests → Enable Access requests → Manual review, reload
//
// Selectors are roles and labels only. Each step asserts the visible state and the write it fires.
import { expect, test, type Locator, type Page } from "@playwright/test";

/** The live sandbox (AGENTS.md "Live sandbox"); the clone's built-in seeds hold the same repo. */
export const REPO = process.env.E2E_REPO ?? "OwnerOfTheGatedModel/tiny-gated-model";
export const REQUESTER = "TestingBOrig";

const DEFAULT_HEADING = "You need to agree to share your contact information to access this model";
const SUBMIT = "Agree and send request to access repo";
const CANCEL_REQUEST = "Cancel my request";
const AWAITING = `Your request to access model ${REPO} is awaiting a review from the repo authors.`;
const REJECTED = "Your request to access this repo has been rejected by the repo's authors.";
const ENABLED = "Access requests are currently enabled for this model.";
const DISABLED = "Access requests are currently disabled for this model.";
const GITATTRIBUTES_FIRST_LINE = "*.7z filter=lfs diff=lfs merge=lfs -text";

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
export async function fires(page: Page, method: "POST" | "PUT", suffix: string, body: unknown, action: () => Promise<unknown>) {
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

/** Steps 1–7. The caller puts the backend in the initial state first and checks the end state after. */
export async function runJourney(page: Page) {
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

  await test.step("1b. requester cancels the pending request, then sends it again (Q-3)", async () => {
    // [OBS 2026-10-06 requester-cancel c2]: self-cancel deletes a pending request; the gate form is back (A2).
    // The browser posts the web route; the backend call it makes (POST …/user-access-request/cancel)
    // is checked by the exchange-log diff.
    const [cancelled] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && new URL(r.url()).pathname === "/-/cancel-request"),
      page.getByRole("button", { name: CANCEL_REQUEST }).click(),
    ]);
    expect(cancelled.status(), "POST /-/cancel-request").toBe(303);
    await expect(page.getByRole("button", { name: SUBMIT })).toBeVisible();
    await expect(page.getByText(AWAITING)).toHaveCount(0);
    await expect(page.getByRole("button", { name: CANCEL_REQUEST })).toHaveCount(0);
    await page.getByRole("button", { name: SUBMIT }).click();
    await expect(page.getByText(AWAITING)).toBeVisible();
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
}
