// The scripted UI walkthrough, shared by the clone run (`clone-walkthrough.spec.ts`) and the live run
// through the bridge (`live-walkthrough.spec.ts`): the SAME journey drives both backends, and the
// clone's exchange log is diffed against the bridge log of the live run.
//
//   1. requester (request in `reset`) submits the consent form
//   1b. requester cancels the pending request from /settings/gated-repos (self-cancel, REQ-7) and
//       submits it again
//   2. owner: Review access requests → search, row selection (no write) → Accept, Escape
//   3. requester: "Gated model" block instead of the gate box, opens .gitattributes
//   4. owner: Cancel (accepted tab), then Reject (pending tab)
//   5. requester: sees the rejected text
//   6. owner: Accept (rejected tab), then Cancel (accepted tab)
//   7. owner: New requests Automatic → Manual, Add access dialog (opened and closed, no write),
//      Notifications frequency Real-time → Once a day, Disable Access requests → Enable Access
//      requests → Manual review, reload
//
// Selectors are roles and labels only. Each step asserts the visible state and the write it fires.
// The screens follow HF's logged-in UI as captured on 2026-10-06
// (docs/hf-gated/observations/2026-10-06-ui-logged-in.md).
import { expect, test, type Locator, type Page } from "@playwright/test";

/** The live sandbox (AGENTS.md "Live sandbox"); the clone's built-in seeds hold the same repo. */
export const REPO = process.env.E2E_REPO ?? "OwnerOfTheGatedModel/tiny-gated-model";
export const REQUESTER = "TestingBOrig";

const DEFAULT_HEADING = "You need to agree to share your contact information to access this model";
// The sandbox is in manual mode with no custom button: the manual default label.
const SUBMIT = "Agree and send request to access repo";
const CANCEL_REQUEST = "Cancel this access request";
const AWAITING =
  "Your request to access this repository has been submitted and is awaiting a review from the repository " +
  "authors. You can check the status of all your access requests in your settings.";
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
// Tabs are plain buttons [OBS-UI 2026-10-06]; ours mark the shown list with aria-current.
const tabOf = (dialog: Locator, status: string, count: number) =>
  dialog.getByRole("button", { name: `${status} (${count})`, exact: true });
const expectCurrentTab = (tab: Locator) => expect(tab).toHaveAttribute("aria-current", "true");
const hasFlag = (flag: string) => (url: URL) => url.searchParams.get(flag) === "true";
const lacksFlag = (flag: string) => (url: URL) => !url.searchParams.has(flag);
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
    // [OBS-UI 2026-10-06] no Cancel button; the form posts to /{repo}/ask-access?next=/{repo}.
    await expect(page.getByRole("button", { name: "Cancel" })).toHaveCount(0);
    const [submitted] = await Promise.all([
      page.waitForRequest((r) => r.method() === "POST" && new URL(r.url()).pathname === `/${REPO}/ask-access`),
      page.getByRole("button", { name: SUBMIT }).click(),
    ]);
    expect(new URL(submitted.url()).searchParams.get("next")).toBe(`/${REPO}`);
    // ask-access → 303 → repo page, now pending (A3), with HF's text and no cancel control.
    await expect(page.getByText(AWAITING)).toBeVisible();
    await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
    await expect(page.getByRole("button", { name: CANCEL_REQUEST })).toHaveCount(0);
  });

  await test.step("1b. requester cancels from /settings/gated-repos, then sends the request again (REQ-7)", async () => {
    // [OBS-UI 2026-10-06] "your settings" → /settings/gated-repos, where the row's icon button titled
    // "Cancel this access request" asks a native confirm(), then sends POST …/user-access-request/cancel
    // (no body) and the row disappears without a reload. [OBS 2026-10-06 requester-cancel c2]: a pending
    // request is deleted, so the gate form is back (A2).
    await page.getByRole("link", { name: "your settings" }).click();
    await expect(page).toHaveURL((url) => url.pathname === "/settings/gated-repos");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: "Gated Repos Status" })).toBeVisible();
    const row = page.getByRole("row").filter({ has: page.getByRole("link", { name: REPO, exact: true }) });
    await expect(row.getByRole("cell", { name: "model", exact: true })).toBeVisible();
    await expect(row.getByRole("cell", { name: "PENDING", exact: true })).toBeVisible();
    // Playwright dismisses dialogs by default: accept the confirm() explicitly, or nothing is sent.
    const asked: string[] = [];
    page.once("dialog", async (dialog) => {
      asked.push(`${dialog.type()}: ${dialog.message()}`);
      await dialog.accept();
    });
    const [cancelled] = await Promise.all([
      page.waitForResponse(
        (r) => r.request().method() === "POST" && new URL(r.url()).pathname === `/api/models/${REPO}/user-access-request/cancel`,
      ),
      row.getByRole("button", { name: CANCEL_REQUEST }).click(),
    ]);
    expect(asked).toEqual(["confirm: Are you sure you want to cancel this access request?"]);
    expect(cancelled.status(), "POST …/user-access-request/cancel").toBe(200);
    expect(cancelled.request().postData()).toBeNull();
    await expect(page.getByRole("link", { name: REPO, exact: true })).toHaveCount(0);
    await expect(page).toHaveURL((url) => url.pathname === "/settings/gated-repos");

    await page.goto(`/${REPO}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: SUBMIT })).toBeVisible();
    await expect(page.getByText(AWAITING)).toHaveCount(0);
    await page.getByRole("button", { name: SUBMIT }).click();
    await expect(page.getByText(AWAITING)).toBeVisible();
  });

  await test.step("2. owner opens Review access requests (1) and accepts TestingBOrig", async () => {
    await actAs(page, "owner", `/${REPO}/settings`);
    await expect(page.getByText(ENABLED)).toBeVisible();
    await expect(page.getByLabel("New requests:")).toHaveValue("manual");
    const dialog = await openReviewModal(page, 1);
    await expect(page).toHaveURL(hasFlag("gated_access_request"));
    await expectCounts(dialog, { pending: 1, accepted: 0, rejected: 0 });
    await expectCurrentTab(tabOf(dialog, "pending", 1));
    const row = rowOf(dialog, REQUESTER);
    await expect(row.getByRole("button", { name: "Accept" })).toBeVisible();
    await expect(row.getByRole("button", { name: "Reject" })).toBeVisible();

    // Search (current tab only, debounced) and row selection [OBS-UI 2026-10-06]: reads only.
    const search = dialog.getByRole("searchbox");
    await expect(search).toHaveAttribute("placeholder", "Search requests");
    await Promise.all([
      page.waitForResponse((r) => {
        const url = new URL(r.url());
        return url.pathname === `/api/models/${REPO}/user-access-request/pending` && url.searchParams.get("q") === "testing";
      }),
      search.fill("testing"),
    ]);
    await expect(dialog.getByText("1 matching result")).toBeVisible();
    await search.fill("");
    await expect(dialog.getByText(/matching result/)).toHaveCount(0);
    const box = row.getByRole("checkbox", { name: `Select access request from ${REQUESTER}` });
    await box.check();
    await expect(dialog.getByText("1 selected")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Accept selected" })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Reject selected" })).toBeVisible();
    await box.uncheck();
    await expect(dialog.getByRole("button", { name: "Accept selected" })).toHaveCount(0);

    await handle(page, "accepted", () => row.getByRole("button", { name: "Accept" }).click());
    // The UI refetches the three lists ~1 s later: the row leaves the pending tab, N drops to 0.
    await expectCounts(dialog, { pending: 0, accepted: 1, rejected: 0 });
    await expect(dialog.getByRole("listitem")).toHaveCount(0);
    await expect(reviewButton(page, 0)).toBeVisible();
    // Escape closes the native dialog and drops the URL flag [OBS-UI 2026-10-06].
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(lacksFlag("gated_access_request"));
  });

  await test.step("3. requester: the Gated model block instead of the gate box, downloads .gitattributes", async () => {
    await actAs(page, "requester", `/${REPO}`);
    // [OBS-UI 2026-10-06] seen as the owner; presumed the same for an accepted requester (Q-11).
    await expect(page.getByRole("heading", { name: "Gated model" })).toBeVisible();
    await expect(page.getByText("You have been granted access to this model")).toBeVisible();
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
    await expectCurrentTab(tabOf(dialog, "accepted", 1));
    const acceptedRow = rowOf(dialog, REQUESTER);
    await expect(acceptedRow.getByRole("button", { name: "Reject" })).toBeVisible();
    await expect(acceptedRow.getByRole("button", { name: "Accept" })).toHaveCount(0);
    await handle(page, "pending", () => acceptedRow.getByRole("button", { name: "Cancel" }).click());
    await expectCounts(dialog, { pending: 1, accepted: 0, rejected: 0 });
    await expect(dialog.getByRole("listitem")).toHaveCount(0); // still on the (now empty) accepted tab

    await tabOf(dialog, "pending", 1).click();
    await expectCurrentTab(tabOf(dialog, "pending", 1));
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
    await expectCurrentTab(tabOf(dialog, "rejected", 1));
    const rejectedRow = rowOf(dialog, REQUESTER);
    await expect(rejectedRow.getByRole("button", { name: "Cancel" })).toBeVisible();
    await handle(page, "accepted", () => rejectedRow.getByRole("button", { name: "Accept" }).click());
    await expectCounts(dialog, { pending: 0, accepted: 1, rejected: 0 });

    await tabOf(dialog, "accepted", 1).click();
    await expectCurrentTab(tabOf(dialog, "accepted", 1));
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

    // Add access [OBS-UI 2026-10-06]: opened and closed, nothing granted (the user search differs
    // between the Hub, which finds nobody, and the clone, so its results are not asserted).
    await Promise.all([
      page.waitForResponse((r) => {
        const url = new URL(r.url());
        return url.pathname === "/api/quicksearch" && url.searchParams.get("q") === "" && url.searchParams.get("type") === "user";
      }),
      addAccess.click(),
    ]);
    const addDialog = page.getByRole("dialog", { name: "Add a user access manually" });
    await expect(addDialog.getByPlaceholder("Start typing to search for a user")).toBeVisible();
    await expect(addDialog.getByRole("button", { name: "Grant access" })).toBeDisabled();
    await expect(page).toHaveURL(hasFlag("gated_add_user"));
    await page.keyboard.press("Escape");
    await expect(addDialog).toHaveCount(0);
    await expect(page).toHaveURL(lacksFlag("gated_add_user"));

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
