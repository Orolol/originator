// `/settings/gated-repos` table [OBS-UI 2026-10-06]: header buttons, one row per request, HF's
// self-cancel button on PENDING and REJECTED rows as HF shows it [OBS-UI], behind a native confirm().
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { CONFIRM_CANCEL, GatedReposTable } from "./GatedReposTable";
import type { GatedRepoRow } from "@/lib/gatedRepos";

const REPO = "OwnerOfTheGatedModel/tiny-gated-model";

const row = (repo: string, status: GatedRepoRow["status"]): GatedRepoRow => ({ repo, type: "model", date: null, status });

describe("GatedReposTable", () => {
  it("renders HF's header buttons and a pending row with the icon-only cancel button", () => {
    render(<GatedReposTable rows={[row(REPO, "pending")]} />);
    const [header, body] = screen.getAllByRole("rowgroup");
    expect(within(header).getAllByRole("button").map((b) => b.textContent)).toEqual([
      "Repo Name",
      "Type",
      "Date",
      "Request Status",
    ]);
    const cells = within(body).getAllByRole("cell");
    expect(within(cells[0]).getByRole("link", { name: REPO }).getAttribute("href")).toBe(`/${REPO}`);
    expect(cells.slice(1, 4).map((c) => c.textContent)).toEqual(["model", "", "PENDING"]);

    const cancel = within(cells[4]).getByRole("button", { name: "Cancel this access request" });
    expect(cancel.getAttribute("title")).toBe("Cancel this access request");
    expect(cancel.textContent).toBe("✕"); // icon only (aria-hidden)
  });

  it.each([
    ["OK", true, [{ method: "POST", url: `/api/models/${REPO}/user-access-request/cancel`, body: undefined }], 0],
    ["Cancel", false, [], 1],
  ])("cancel button: confirm() answered %s", async (_answer, confirmed, sent, rowsLeft) => {
    const confirm = vi.fn(() => confirmed);
    vi.stubGlobal("confirm", confirm);
    const calls: { method: string; url: string; body: unknown }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init: RequestInit = {}) => {
        calls.push({ method: init.method ?? "GET", url, body: init.body });
        return Response.json({ ok: true });
      }),
    );
    render(<GatedReposTable rows={[row(REPO, "pending")]} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancel this access request" }));
    expect(confirm).toHaveBeenCalledWith(CONFIRM_CANCEL);
    // The row disappears without a reload once the backend accepted the cancel.
    await waitFor(() => expect(screen.queryAllByRole("link", { name: REPO })).toHaveLength(rowsLeft));
    expect(calls).toEqual(sent);
  });

  it("a refused cancel keeps the row and shows the backend error", async () => {
    vi.stubGlobal("confirm", () => true);
    const message = "No pending access request found for this repo and this user";
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: message }, { status: 404 })));
    render(<GatedReposTable rows={[row(REPO, "pending")]} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancel this access request" }));
    expect((await screen.findByRole("alert")).textContent).toContain(message);
    expect(screen.getByRole("link", { name: REPO })).toBeTruthy();
  });

  it.each([
    ["pending", true],
    ["rejected", true], // [OBS-UI 2026-10-06]: HF keeps the button on a REJECTED row
    ["reset", false], // Provisional (Q-3): never seen
  ] as const)("a %s row: cancel button shown = %s", (status, shown) => {
    render(<GatedReposTable rows={[row("a/b", status)]} />);
    expect(screen.getByRole("cell", { name: status.toUpperCase() })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Cancel this access request" }) !== null).toBe(shown);
  });

  it("no request → an empty table", () => {
    render(<GatedReposTable rows={[]} />);
    expect(within(screen.getAllByRole("rowgroup")[1]).queryAllByRole("row")).toHaveLength(0);
  });

  it("a header button sorts by its column, a second click reverses", () => {
    render(<GatedReposTable rows={[row("b/x", "pending"), row("a/y", "rejected"), row("c/z", "reset")]} />);
    const repos = () => screen.getAllByRole("link").map((a) => a.textContent);
    expect(repos()).toEqual(["b/x", "a/y", "c/z"]);
    fireEvent.click(screen.getByRole("button", { name: "Repo Name" }));
    expect(repos()).toEqual(["a/y", "b/x", "c/z"]);
    fireEvent.click(screen.getByRole("button", { name: "Repo Name" }));
    expect(repos()).toEqual(["c/z", "b/x", "a/y"]);
    fireEvent.click(screen.getByRole("button", { name: "Request Status" }));
    expect(repos()).toEqual(["b/x", "a/y", "c/z"]);
  });
});
