// Read-only walkthrough against the live backend (sandbox repo, docs/system.md personas).
// NEVER clicks a state-changing control; as a safety net every non-GET/HEAD browser request is
// aborted and fails the test.
import { expect, test, type Page } from "@playwright/test";

const REPO = process.env.E2E_REPO ?? "OwnerOfTheGatedModel/tiny-gated-model";
const DEFAULT_HEADING = "You need to agree to share your contact information to access this model";
const SUBMIT = "Agree and send request to access repo";

let attemptedWrites: string[] = [];

test.beforeEach(async ({ page }) => {
  attemptedWrites = [];
  await page.route("**/*", (route) => {
    const req = route.request();
    if (req.method() === "GET" || req.method() === "HEAD") return route.continue();
    attemptedWrites.push(`${req.method()} ${req.url()}`);
    return route.abort();
  });
});

test.afterEach(() => {
  expect(attemptedWrites, "state-changing requests attempted").toEqual([]);
});

async function actAs(page: Page, persona: string, path: string) {
  await page.goto(`/-/persona?as=${persona}&next=${encodeURIComponent(path)}`);
  await expect(page).toHaveURL(new RegExp(`${path}$`));
}

test("anonymous sees A1: texts, log-in line, no form (ui.md §A1)", async ({ page }) => {
  await actAs(page, "anonymous", `/${REPO}`);
  await expect(page.getByRole("heading", { name: DEFAULT_HEADING })).toBeVisible();
  await expect(
    page.getByText(
      "This repository is publicly accessible, but you have to accept the conditions to access its files and content.",
    ),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign Up" })).toBeVisible();
  await expect(page.getByText("to review the conditions and access this model content.")).toBeVisible();
  await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
  await expect(page.locator("form")).toHaveCount(0);
  // ACC-4: the file list stays public and links to resolve.
  await expect(page.getByRole("link", { name: "README.md", exact: true })).toHaveAttribute(
    "href",
    `/${REPO}/resolve/main/README.md`,
  );
});

test("requester with a pending request sees the awaiting-review message (A3, provisional Q-11)", async ({ page }) => {
  await actAs(page, "requester", `/${REPO}`);
  await expect(page.getByText("Acting as requester (TestingBOrig)")).toBeVisible();
  await expect(
    page.getByText(`Your request to access model ${REPO} is awaiting a review from the repo authors.`),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
});

test("owner sees no gate box on the model page (ACC-1)", async ({ page }) => {
  await actAs(page, "owner", `/${REPO}`);
  await expect(page.getByRole("heading", { name: REPO })).toBeVisible();
  await expect(page.getByRole("heading", { name: DEFAULT_HEADING })).toHaveCount(0);
});

test("owner settings: enabled, Manual review, modal lists TestingBOrig as pending (ui.md §B3, §C)", async ({ page }) => {
  const listRequests: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/user-access-request/")) listRequests.push(`${req.method()} ${new URL(req.url()).pathname}`);
  });
  await actAs(page, "owner", `/${REPO}/settings`);
  await expect(page.getByText("Access requests are currently enabled for this model.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Disable Access requests" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "New requests:" })).toHaveValue("manual");
  await expect(page.getByRole("button", { name: "Add access" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Notifications frequency" })).toBeVisible();
  await expect(page.getByPlaceholder("example@example.com")).toBeVisible();

  await page.getByRole("button", { name: /^Review access requests/ }).click();
  const dialog = page.getByRole("dialog", { name: "Manage access requests" });
  await expect(dialog).toBeVisible();
  const pendingTab = dialog.getByRole("tab", { name: /^pending \(\d+\)$/ });
  await expect(pendingTab).toHaveAttribute("aria-selected", "true");
  const row = dialog.getByRole("listitem").filter({ has: page.getByRole("link", { name: "TestingBOrig" }) });
  await expect(row.getByRole("button", { name: "Accept" })).toBeVisible();
  await expect(row.getByRole("button", { name: "Reject" })).toBeVisible();
  // Same requests as HF's list API, fired by the browser on the web origin.
  expect(listRequests.sort()).toEqual(
    ["accepted", "pending", "rejected"].map((s) => `GET /api/models/${REPO}/user-access-request/${s}`),
  );

  for (const name of ["accepted", "rejected", "pending"]) {
    const tab = dialog.getByRole("tab", { name: new RegExp(`^${name} \\(\\d+\\)$`) });
    await tab.click();
    await expect(tab).toHaveAttribute("aria-selected", "true");
  }
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(dialog).toHaveCount(0);
});

test("owner downloads the user access report (REP-1)", async ({ page }) => {
  await actAs(page, "owner", `/${REPO}/settings`);
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download user access report" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe(`user-access-report-${REPO.replace("/", "-")}.json`);
});
