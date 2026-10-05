// Owner controls → requests fired (ui.md §D side-effect matrix). fetch is mocked: method, path and
// JSON body are asserted, nothing reaches a backend.
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { GatedUserAccess } from "./GatedUserAccess";
import { accessRequest } from "@/test/fixtures";
import type { Gated } from "@/lib/hubClient";

const REPO = "Orosius/deltanet-mla-latent";
const API = `/api/models/${REPO}`;

interface Call {
  method: string;
  url: string;
  body: unknown;
}

type Route = (call: Call) => Response | undefined;

/** Records every call; answers from `route`, else echoes the JSON body with 200. */
function mockFetch(route: Route = () => undefined) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const call = { method: init.method ?? "GET", url, body: init.body ? JSON.parse(String(init.body)) : undefined };
      calls.push(call);
      return route(call) ?? Response.json(call.body ?? {});
    }),
  );
  return calls;
}

const lists = {
  pending: [accessRequest("TestingBOrig", "pending", { Affiliation: "Originator" })],
  accepted: [accessRequest("AcceptedUser", "accepted")],
  rejected: [accessRequest("RejectedUser", "rejected")],
};

function listRoute(call: Call): Response | undefined {
  const m = call.method === "GET" && call.url.match(/\/user-access-request\/(pending|accepted|rejected)$/);
  return m ? Response.json(lists[m[1] as keyof typeof lists]) : undefined;
}

function renderSection(gated: Gated, pending: number | null = 1) {
  render(<GatedUserAccess repoId={REPO} initialGated={gated} initialPendingCount={pending} refreshDelayMs={0} />);
}

const writes = (calls: Call[]) => calls.filter((c) => c.method !== "GET");

/** Paragraph whose whole text (including the <strong> badge) equals `text`. */
const fullText = (text: string) => (_: string, el: Element | null) => el?.tagName === "P" && el.textContent === text;

describe("settings section (ui.md §B)", () => {
  it("B1 → Enable Access requests sends PUT {gated:'auto'} (CFG-1) and shows B2", async () => {
    const calls = mockFetch();
    renderSection(false, null);
    expect(screen.getByText(fullText("Access requests are currently disabled for this model."))).toBeTruthy();
    expect(screen.queryByRole("combobox", { name: "New requests:" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Enable Access requests" }));
    await screen.findByText(fullText("Access requests are currently enabled for this model."));
    expect(writes(calls)).toEqual([{ method: "PUT", url: `${API}/settings`, body: { gated: "auto" } }]);
    expect((screen.getByRole("combobox", { name: "New requests:" }) as HTMLSelectElement).value).toBe("auto");
    expect(screen.getByRole("button", { name: "Disable Access requests" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Add access" })).toBeNull(); // manual only
  });

  it.each([
    ["Disable Access requests", (s: typeof screen) => fireEvent.click(s.getByRole("button", { name: "Disable Access requests" })), { gated: false }],
    ["New requests: Automatic approval", (s: typeof screen) => fireEvent.change(s.getByRole("combobox", { name: "New requests:" }), { target: { value: "auto" } }), { gated: "auto" }],
    ["Notifications frequency", (s: typeof screen) => fireEvent.change(s.getByRole("combobox", { name: "Notifications frequency" }), { target: { value: "real-time" } }), { gatedNotificationsMode: "real-time" }],
    [
      "Notifications email (on blur)",
      (s: typeof screen) => {
        const input = s.getByRole("textbox", { name: "Notifications email" });
        fireEvent.change(input, { target: { value: "owner@example.com" } });
        fireEvent.blur(input);
      },
      { gatedNotificationsEmail: "owner@example.com" },
    ],
  ])("B3 %s → one PUT /settings", async (_name, act, body) => {
    const calls = mockFetch();
    renderSection("manual");
    act(screen);
    await waitFor(() => expect(writes(calls)).toEqual([{ method: "PUT", url: `${API}/settings`, body }]));
  });

  it("B3 shows manual-only controls with HF labels", () => {
    mockFetch();
    renderSection("manual", 1);
    expect((screen.getByRole("combobox", { name: "New requests:" }) as HTMLSelectElement).value).toBe("manual");
    expect(screen.getByRole("button", { name: "Add access" })).toBeTruthy();
    expect((screen.getByRole("combobox", { name: "Notifications frequency" }) as HTMLSelectElement).value).toBe("bulk");
    expect(screen.getByRole("option", { name: "Once a day" })).toBeTruthy();
    expect(screen.getByPlaceholderText("example@example.com")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Review access requests (1)" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Download user access report" })).toBeTruthy();
  });

  it("a refused PUT shows the backend message and keeps the state", async () => {
    mockFetch(() =>
      Response.json(
        { error: "You have read access but not the required permissions for this operation" },
        { status: 403 },
      ),
    );
    renderSection("manual");
    fireEvent.click(screen.getByRole("button", { name: "Disable Access requests" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "You have read access but not the required permissions for this operation",
    );
    expect(screen.getByText(fullText("Access requests are currently enabled for this model."))).toBeTruthy();
  });
});

describe("Manage access requests modal (ui.md §C)", () => {
  async function openModal() {
    fireEvent.click(screen.getByRole("button", { name: "Review access requests (1)" }));
    const dialog = await screen.findByRole("dialog", { name: "Manage access requests" });
    await within(dialog).findByRole("tab", { name: "pending (1)" });
    return dialog;
  }

  it("loads the three lists and renders rows with username link, email, relative time", async () => {
    const calls = mockFetch(listRoute);
    renderSection("manual");
    const dialog = await openModal();
    expect(calls.map((c) => `${c.method} ${c.url}`).sort()).toEqual(
      ["accepted", "pending", "rejected"].map((s) => `GET ${API}/user-access-request/${s}`),
    );
    expect(within(dialog).getByRole("tab", { name: "pending (1)" }).getAttribute("aria-selected")).toBe("true");
    const panel = within(dialog).getByRole("tabpanel");
    expect(within(panel).getByRole("link", { name: "TestingBOrig" }).getAttribute("href")).toBe("/TestingBOrig");
    expect(panel.textContent).toContain("testingborig@example.com");
    expect(panel.textContent).toContain("less than a minute ago");
    expect(panel.textContent).toContain("Originator"); // fields answers
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it.each([
    ["pending", "TestingBOrig", "Accept", "accepted"],
    ["pending", "TestingBOrig", "Reject", "rejected"],
    ["accepted", "AcceptedUser", "Reject", "rejected"],
    ["accepted", "AcceptedUser", "Cancel", "pending"],
    ["rejected", "RejectedUser", "Accept", "accepted"],
    ["rejected", "RejectedUser", "Cancel", "pending"],
  ])("%s tab: %s / %s → POST handle {user, status:%s}, then lists refetched", async (tab, user, label, status) => {
    const calls = mockFetch(listRoute);
    renderSection("manual");
    const dialog = await openModal();
    fireEvent.click(within(dialog).getByRole("tab", { name: `${tab} (1)` }));
    const panel = within(dialog).getByRole("tabpanel");
    expect(within(panel).getAllByRole("button").map((b) => b.textContent)).toEqual(
      tab === "pending" ? ["Accept", "Reject"] : tab === "accepted" ? ["Reject", "Cancel"] : ["Accept", "Cancel"],
    );
    fireEvent.click(within(panel).getByRole("button", { name: label }));
    await waitFor(() => expect(calls.filter((c) => c.method === "GET")).toHaveLength(6));
    expect(writes(calls)).toEqual([{ method: "POST", url: `${API}/user-access-request/handle`, body: { user, status } }]);
  });

  it("Add access: quicksearch users, then POST grant {user}", async () => {
    const calls = mockFetch((call) => {
      if (call.url.startsWith("/api/quicksearch")) return Response.json({ users: [{ user: "TestingBOrig", fullname: "Bridge" }] });
      return listRoute(call);
    });
    renderSection("manual");
    fireEvent.click(screen.getByRole("button", { name: "Add access" }));
    const dialog = await screen.findByRole("dialog", { name: "Add access" });
    fireEvent.change(within(dialog).getByRole("searchbox"), { target: { value: "Testing" } });
    fireEvent.click(await within(dialog).findByRole("button", { name: "TestingBOrig" }));
    await waitFor(() => expect(writes(calls)).toHaveLength(1));
    expect(calls[0]).toEqual({ method: "GET", url: "/api/quicksearch?q=Testing&type=user", body: undefined });
    expect(writes(calls)).toEqual([{ method: "POST", url: `${API}/user-access-request/grant`, body: { user: "TestingBOrig" } }]);
  });
});
