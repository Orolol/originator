// Owner controls → requests fired (ui.md §D side-effect matrix; review modal and Add access as recorded
// [OBS-UI 2026-10-06]). fetch is mocked: method, path, query and JSON body are asserted, nothing
// reaches a backend.
import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { GatedUserAccess } from "./GatedUserAccess";
import { accessRequest, userId } from "@/test/fixtures";
import type { Gated } from "@/lib/hubClient";

const REPO = "Orosius/deltanet-mla-latent";
const API = `/api/models/${REPO}`;

interface Call {
  method: string;
  url: string;
  body: unknown;
}

type Route = (call: Call) => Response | undefined;

/** Records every call; answers from `route`, else echoes the JSON body with 200. URLs are kept as fired. */
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

type Lists = Record<"pending" | "accepted" | "rejected", ReturnType<typeof accessRequest>[]>;

const LISTS: Lists = {
  pending: [accessRequest("TestingBOrig", "pending", { Affiliation: "Originator" })],
  accepted: [accessRequest("AcceptedUser", "accepted")],
  rejected: [accessRequest("RejectedUser", "rejected")],
};

const LIST_URL = /^\/api\/models\/[^?]+\/user-access-request\/(pending|accepted|rejected)\?(.*)$/;

/**
 * The owner list endpoint (REV-10): `q` = case-insensitive username prefix (REV-10 [OBS]); pages of
 * `pageSize` items addressed by a `page` parameter, with `Link: <…>; rel="next"` written on the web
 * origin like the proxy does.
 */
function listRoute(lists: Lists = LISTS, pageSize = 100): Route {
  return (call) => {
    const m = call.method === "GET" && call.url.match(LIST_URL);
    if (!m) return undefined;
    const params = new URLSearchParams(m[2]);
    const q = (params.get("q") ?? "").toLowerCase();
    const matching = lists[m[1] as keyof Lists].filter((r) => r.user.user.toLowerCase().startsWith(q));
    const page = Number(params.get("page") ?? 0);
    const headers: Record<string, string> = {};
    if (matching.length > (page + 1) * pageSize) {
      params.set("page", String(page + 1));
      headers.link = `<http://localhost:3000${call.url.split("?")[0]}?${params}>; rel="next"`;
    }
    return Response.json(matching.slice(page * pageSize, (page + 1) * pageSize), { headers });
  };
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
        expect(input.getAttribute("type")).toBe("email"); // [OBS-UI 2026-10-06]
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

const listGets = (calls: Call[]) => calls.filter((c) => c.method === "GET" && LIST_URL.test(c.url)).map((c) => c.url);

describe("Manage access requests modal (ui.md §C) [OBS-UI 2026-10-06]", () => {
  async function openModal(pendingLabel = "pending (1)") {
    fireEvent.click(screen.getByRole("button", { name: /^Review access requests/ }));
    const dialog = await screen.findByRole("dialog", { name: "Manage access requests" });
    await within(dialog).findByRole("button", { name: pendingLabel });
    return dialog;
  }

  const rowOf = (dialog: HTMLElement, user: string) =>
    within(dialog)
      .getAllByRole("listitem")
      .find((li) => within(li).queryByRole("link", { name: user }))!;

  it("is a native <dialog> flagged in the URL; opening fetches the three lists with limit=100; tabs are plain buttons", async () => {
    const calls = mockFetch(listRoute());
    renderSection("manual");
    const dialog = await openModal();
    expect(dialog.tagName).toBe("DIALOG");
    expect((dialog as HTMLDialogElement).open).toBe(true);
    expect(window.location.search).toBe("?gated_access_request=true");
    expect(listGets(calls).sort()).toEqual(
      ["accepted", "pending", "rejected"].map((s) => `${API}/user-access-request/${s}?limit=100`),
    );
    expect(within(dialog).queryAllByRole("tab")).toHaveLength(0);
    for (const label of ["pending (1)", "accepted (1)", "rejected (1)"]) {
      expect(within(dialog).getByRole("button", { name: label })).toBeTruthy();
    }
    expect(within(dialog).queryByRole("button", { name: /^reset/ })).toBeNull();
    expect(within(dialog).getByRole("button", { name: "pending (1)" }).getAttribute("aria-current")).toBe("true");
    expect(within(dialog).getByRole("searchbox").getAttribute("placeholder")).toBe("Search requests");

    const row = rowOf(dialog, "TestingBOrig");
    const box = within(row).getByRole("checkbox", { name: "Select access request from TestingBOrig" });
    expect(box.getAttribute("value")).toBe(userId("TestingBOrig"));
    expect(within(row).getByRole("link", { name: "TestingBOrig" }).getAttribute("href")).toBe("/TestingBOrig");
    expect(row.textContent).toContain("testingborig@example.com");
    expect(row.textContent).toContain("less than a minute ago");
    expect(row.textContent).toContain("Originator"); // fields answers
    expect(within(dialog).getByText("Previous").hasAttribute("href")).toBe(false); // one page only
    expect(within(dialog).getByText("Next").hasAttribute("href")).toBe(false);

    // The close button (and Escape, in a browser) closes the native dialog: removed, flag gone.
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.location.search).toBe("");
  });

  it.each([
    ["pending", "TestingBOrig", "Accept", "accepted"],
    ["pending", "TestingBOrig", "Reject", "rejected"],
    ["accepted", "AcceptedUser", "Reject", "rejected"],
    ["accepted", "AcceptedUser", "Cancel", "pending"],
    ["rejected", "RejectedUser", "Accept", "accepted"],
    ["rejected", "RejectedUser", "Cancel", "pending"],
  ])("%s tab: %s / %s → POST handle {user, status:%s}, then the source and destination lists refetched", async (tab, user, label, status) => {
    const calls = mockFetch(listRoute());
    renderSection("manual");
    const dialog = await openModal();
    if (tab !== "pending") {
      // Switching tabs refetches that tab's list [OBS-UI 2026-10-06].
      fireEvent.click(within(dialog).getByRole("button", { name: `${tab} (1)` }));
      await waitFor(() => expect(listGets(calls).slice(3)).toEqual([`${API}/user-access-request/${tab}?limit=100`]));
    }
    const before = listGets(calls).length;
    const row = await waitFor(() => rowOf(dialog, user));
    expect(within(row).getAllByRole("button").map((b) => b.textContent)).toEqual(
      tab === "pending" ? ["Accept", "Reject"] : tab === "accepted" ? ["Reject", "Cancel"] : ["Accept", "Cancel"],
    );
    fireEvent.click(within(row).getByRole("button", { name: label }));
    await waitFor(() => expect(listGets(calls)).toHaveLength(before + 2));
    expect(listGets(calls).slice(before).sort()).toEqual(
      [tab, status].sort().map((s) => `${API}/user-access-request/${s}?limit=100`),
    );
    expect(writes(calls)).toEqual([{ method: "POST", url: `${API}/user-access-request/handle`, body: { user, status } }]);
    expect(within(dialog).getByRole("button", { name: new RegExp(`^${tab} `) }).getAttribute("aria-current")).toBe("true");
  });

  it("shows Processing... while a tab loads, then 'No <status> access requests' for an empty one", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    const lists = { ...LISTS, accepted: [] };
    mockFetch(listRoute(lists));
    renderSection("manual");
    const dialog = await openModal();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        await gate;
        return listRoute(lists)({ method: "GET", url, body: undefined })!;
      }),
    );
    fireEvent.click(within(dialog).getByRole("button", { name: "accepted (0)" }));
    expect(within(dialog).getByText("Processing...")).toBeTruthy();
    expect(within(dialog).queryByText("No accepted access requests")).toBeNull();
    release();
    expect(await within(dialog).findByText("No accepted access requests")).toBeTruthy();
    expect(within(dialog).queryByText("Processing...")).toBeNull();
  });

  it("search queries the current tab only, debounced, and shows the matching count", async () => {
    const lists = { ...LISTS, pending: [...LISTS.pending, accessRequest("DemoCarol", "pending")] };
    const calls = mockFetch(listRoute(lists));
    renderSection("manual");
    const dialog = await openModal("pending (2)");
    const search = within(dialog).getByRole("searchbox");
    fireEvent.change(search, { target: { value: "t" } });
    fireEvent.change(search, { target: { value: "testing" } });
    expect(await within(dialog).findByText("1 matching result")).toBeTruthy();
    expect(listGets(calls).slice(3)).toEqual([`${API}/user-access-request/pending?limit=100&q=testing`]);
    expect(within(dialog).getAllByRole("listitem")).toHaveLength(1);
    // Clearing the box shows the whole first page again, without a request.
    fireEvent.change(search, { target: { value: "" } });
    expect(within(dialog).getAllByRole("listitem")).toHaveLength(2);
    expect(within(dialog).queryByText(/matching result/)).toBeNull();
    expect(listGets(calls)).toHaveLength(4);
  });

  it.each([
    ["Accept selected", "accepted"],
    ["Reject selected", "rejected"],
  ])("bulk: Select all → n selected → %s → POST batch {status:%s, requests:[{userId}]}, then refetch", async (label, status) => {
    const lists = { ...LISTS, pending: [...LISTS.pending, accessRequest("DemoCarol", "pending")] };
    const calls = mockFetch((call) =>
      call.url.endsWith("/batch")
        ? Response.json([{ userId: userId("TestingBOrig"), ok: true }, { userId: userId("DemoCarol"), ok: true }])
        : listRoute(lists)(call),
    );
    renderSection("manual");
    const dialog = await openModal("pending (2)");
    expect(within(dialog).queryByRole("button", { name: label })).toBeNull();
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Select access request from DemoCarol" }));
    expect(within(dialog).getByText("1 selected")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Select all" }));
    expect(within(dialog).getByText("2 selected")).toBeTruthy();
    expect(within(dialog).getByRole("button", { name: "Accept selected" })).toBeTruthy();
    expect(within(dialog).getByRole("button", { name: "Reject selected" })).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: label }));
    await waitFor(() => expect(listGets(calls)).toHaveLength(5)); // 3 on open + current tab and destination
    expect(writes(calls)).toEqual([
      {
        method: "POST",
        url: `${API}/user-access-request/batch`,
        // Select all takes the rows in list order.
        body: { status, requests: [{ userId: userId("TestingBOrig") }, { userId: userId("DemoCarol") }] },
      },
    ]);
    await waitFor(() => expect(within(dialog).queryByText(/selected$/)).toBeNull());
  });

  it("a failed batch item is reported, not swallowed", async () => {
    mockFetch((call) =>
      call.url.endsWith("/batch")
        ? Response.json([{ userId: userId("TestingBOrig"), ok: false, error: "request_not_found" }])
        : listRoute()(call),
    );
    renderSection("manual");
    const dialog = await openModal();
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Select access request from TestingBOrig" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Accept selected" }));
    expect((await within(dialog).findByRole("alert")).textContent).toContain(`${userId("TestingBOrig")}: request_not_found`);
  });

  it("Next follows the list's Link rel=next through the web /api proxy; Previous goes back", async () => {
    const names = ["Ann", "Bob", "Cid", "Dee", "Eve", "Fay", "Gus", "Hal", "Ivy", "Jon", "Kim", "Lou"];
    const lists = { ...LISTS, pending: names.map((n) => accessRequest(n, "pending")) };
    const calls = mockFetch(listRoute(lists, 10));
    renderSection("manual");
    const dialog = await openModal("pending (10)");
    const pageNames = () => within(dialog).getAllByRole("listitem").map((li) => within(li).getByRole("link").textContent);
    expect(pageNames()).toEqual(names.slice(0, 10));
    expect(within(dialog).getByText("Previous").hasAttribute("href")).toBe(false);

    const next = within(dialog).getByRole("link", { name: "Next" });
    expect(next.getAttribute("href")).toBe(`${API}/user-access-request/pending?limit=100&page=1`);
    fireEvent.click(next);
    await waitFor(() => expect(pageNames()).toEqual(names.slice(10)));
    expect(listGets(calls).at(-1)).toBe(`${API}/user-access-request/pending?limit=100&page=1`);
    expect(within(dialog).getByText("Next").hasAttribute("href")).toBe(false);

    fireEvent.click(within(dialog).getByRole("link", { name: "Previous" }));
    await waitFor(() => expect(pageNames()).toEqual(names.slice(0, 10)));
    expect(listGets(calls).at(-1)).toBe(`${API}/user-access-request/pending?limit=100`);
    expect(within(dialog).getByText("Previous").hasAttribute("href")).toBe(false);

    // A page does not survive a tab switch: back on pending, its refetched first page is shown.
    fireEvent.click(within(dialog).getByRole("link", { name: "Next" }));
    await waitFor(() => expect(pageNames()).toEqual(names.slice(10)));
    fireEvent.click(within(dialog).getByRole("button", { name: "accepted (1)" }));
    fireEvent.click(await within(dialog).findByRole("button", { name: "pending (10)" }));
    await waitFor(() => expect(pageNames()).toEqual(names.slice(0, 10)));
  });
});

describe("Add access dialog [OBS-UI 2026-10-06]", () => {
  it("opens flagged in the URL and searches with an empty q; no users → 'No results found :('", async () => {
    const calls = mockFetch((call) => (call.url.startsWith("/api/quicksearch") ? Response.json({ users: [] }) : undefined));
    renderSection("manual");
    fireEvent.click(screen.getByRole("button", { name: "Add access" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a user access manually" });
    expect(dialog.tagName).toBe("DIALOG");
    expect(window.location.search).toBe("?gated_add_user=true");
    expect(within(dialog).getByPlaceholderText("Start typing to search for a user").getAttribute("type")).toBe("text");
    expect(await within(dialog).findByText("No results found :(")).toBeTruthy();
    expect(calls.map((c) => c.url)).toEqual(["/api/quicksearch?q=&type=user"]);
    expect((within(dialog).getByRole("button", { name: "Grant access" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.location.search).toBe("");
  });

  it("typing searches (debounced); a click selects; Grant access then sends POST grant {user}", async () => {
    const calls = mockFetch((call) => {
      if (call.url.startsWith("/api/quicksearch?q=Testing")) return Response.json({ users: [{ user: "TestingBOrig", fullname: "Bridge" }] });
      if (call.url.startsWith("/api/quicksearch")) return Response.json({ users: [] });
      return listRoute()(call);
    });
    renderSection("manual");
    fireEvent.click(screen.getByRole("button", { name: "Add access" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a user access manually" });
    await within(dialog).findByText("No results found :(");
    fireEvent.change(within(dialog).getByPlaceholderText("Start typing to search for a user"), { target: { value: "Testing" } });
    const result = await within(dialog).findByRole("button", { name: "TestingBOrig" });
    expect(calls.map((c) => c.url)).toEqual(["/api/quicksearch?q=&type=user", "/api/quicksearch?q=Testing&type=user"]);
    fireEvent.click(result);
    expect(result.getAttribute("aria-pressed")).toBe("true");
    expect(writes(calls)).toEqual([]); // selecting does not grant
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Grant access" })));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writes(calls)).toEqual([{ method: "POST", url: `${API}/user-access-request/grant`, body: { user: "TestingBOrig" } }]);
    // The pending count is reread after the grant.
    await waitFor(() => expect(listGets(calls)).toEqual([`${API}/user-access-request/pending?limit=100`]));
  });
});
