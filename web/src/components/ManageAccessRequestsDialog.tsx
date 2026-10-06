"use client";
// Owner modal "Manage access requests" (docs/hf-gated/ui.md §C) [OBS-UI 2026-10-06]: a native
// <dialog> (Escape closes it) that adds `?gated_access_request=true` to the URL while open, fetches the
// three lists with `?limit=100`, has plain-button tabs `pending (n)` / `accepted (n)` / `rejected (n)`
// (no reset tab), a debounced search on the current tab, bulk selection ("Accept selected" / "Reject
// selected") and Previous / Next pagination driven by the lists' `Link: rel="next"` header (REV-10).
// Session 2 [OBS-UI 2026-10-06]: after a row action only the source and destination lists are
// refetched and the current tab stays; switching tabs refetches that tab ("Processing..." meanwhile);
// an empty tab reads "No <status> access requests".
import { useCallback, useEffect, useRef, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import type { BackendError } from "@/lib/httpError";
import {
  accessRequestsUrl,
  batchAccessRequests,
  fetchAccessRequestPage,
  handleAccessRequest,
  type AccessRequest,
  type AccessRequestPage,
  type HandleStatus,
  type RequestStatus,
} from "@/lib/hubClient";
import { setUrlFlag } from "@/lib/urlFlag";
import { ErrorNotice } from "./ErrorNotice";

export const REQUEST_TABS: RequestStatus[] = ["pending", "accepted", "rejected"];

// [OBS-UI 2026-10-06] one debounced request per search; the delay itself is not measured.
export const SEARCH_DEBOUNCE_MS = 300;

const ROW_ACTIONS: Record<RequestStatus, { label: string; status: HandleStatus }[]> = {
  pending: [
    { label: "Accept", status: "accepted" }, // [DOC] [DOC-IMG] [OBS-UI 2026-10-06]
    { label: "Reject", status: "rejected" }, // [OBS-UI 2026-10-06]; Provisional (Q-13): no rejection-reason input
  ],
  accepted: [
    { label: "Reject", status: "rejected" }, // [DOC] [OBS-UI 2026-10-06]
    { label: "Cancel", status: "pending" }, // [DOC] [OBS-UI 2026-10-06] back to pending (REV-4)
  ],
  // Provisional (Q-13): rejected-tab actions are unrecorded (the list was empty); the API allows
  // → accepted and → pending.
  rejected: [
    { label: "Accept", status: "accepted" },
    { label: "Cancel", status: "pending" },
  ],
};

type FirstPages = Record<RequestStatus, AccessRequestPage | null>;
const NO_PAGES: FirstPages = { pending: null, accepted: null, rejected: null };

/** What the current tab shows when it is not its cached first page: a search result or another page. */
interface View {
  tab: RequestStatus;
  q: string;
  page: AccessRequestPage;
  /** URLs of the earlier pages, for Previous. */
  previous: string[];
}

interface Props {
  repoId: string;
  /** Delay before refetching after an action (Q-23 / Q-13, see GatedUserAccess). */
  refreshDelayMs: number;
  /** The pending list's length whenever it is (re)loaded: the settings button shows it. */
  onPendingCount: (count: number) => void;
  onClose: () => void;
}

interface Fetched {
  statuses: RequestStatus[];
  pages: Partial<FirstPages>;
  error: BackendError | null;
}

/** First page of each list, `GET …/{status}?limit=100` [OBS-UI 2026-10-06]. */
async function fetchFirstPages(repoId: string, statuses: RequestStatus[]): Promise<Fetched> {
  const results = await Promise.all(statuses.map((s) => fetchAccessRequestPage(accessRequestsUrl(repoId, s))));
  const pages: Partial<FirstPages> = {};
  let error: BackendError | null = null;
  results.forEach((res, i) => {
    if (res.ok) pages[statuses[i]] = res.data;
    else error ??= res.error;
  });
  return { statuses, pages, error };
}

export function ManageAccessRequestsDialog({ repoId, refreshDelayMs, onPendingCount, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [tab, setTab] = useState<RequestStatus>("pending");
  const [firstPages, setFirstPages] = useState<FirstPages>(NO_PAGES);
  // Lists being (re)fetched; opening fetches all three.
  const [loading, setLoading] = useState<RequestStatus[]>(REQUEST_TABS);
  const [query, setQuery] = useState("");
  const [view, setView] = useState<View | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<BackendError | null>(null);
  const q = query.trim();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    setUrlFlag("gated_access_request", true);
    return () => setUrlFlag("gated_access_request", false);
  }, []);

  const applyFirstPages = useCallback(
    ({ statuses, pages, error: firstError }: Fetched) => {
      setFirstPages((current) => ({ ...current, ...pages }));
      setLoading((current) => current.filter((s) => !statuses.includes(s)));
      setError(firstError);
      // [OBS-UI 2026-10-06] N in "Review access requests (N)" is the pending count.
      if (pages.pending) onPendingCount(pages.pending.items.length);
    },
    [onPendingCount],
  );

  const reloadFirstPages = useCallback(
    async (statuses: RequestStatus[]) => {
      setLoading((current) => [...current, ...statuses.filter((s) => !current.includes(s))]);
      applyFirstPages(await fetchFirstPages(repoId, statuses));
    },
    [repoId, applyFirstPages],
  );

  const showPage = useCallback(async (forTab: RequestStatus, forQ: string, url: string, previous: string[]) => {
    const res = await fetchAccessRequestPage(url);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setError(null);
    setSelected([]);
    setView({ tab: forTab, q: forQ, page: res.data, previous });
  }, []);

  useEffect(() => {
    // [OBS-UI 2026-10-06] opening fires GET …/{pending,accepted,rejected}?limit=100.
    void fetchFirstPages(repoId, REQUEST_TABS).then(applyFirstPages);
  }, [repoId, applyFirstPages]);

  useEffect(() => {
    // [OBS-UI 2026-10-06] a search queries the current tab only, `…/{tab}?limit=100&q=…`, debounced.
    // Provisional (Q-13): switching tabs with a query re-runs it on the new tab; an empty query shows
    // the tab's first page again without a request.
    if (!q) return;
    const timer = setTimeout(() => void showPage(tab, q, accessRequestsUrl(repoId, tab, q), []), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [repoId, tab, q, showPage]);

  // The view only applies to the tab and query it was loaded for.
  const current = view && view.tab === tab && view.q === q ? view : null;
  const page = current?.page ?? (q || loading.includes(tab) ? null : firstPages[tab]);
  const rows = page?.items ?? null;
  const previous = current?.previous ?? [];
  // [OBS-UI 2026-10-06] "Processing..." while the shown list loads (a search counts as loading too).
  const processing = !current && (q !== "" || loading.includes(tab));

  /**
   * After an action, refetch the lists it touched: the source and destination [OBS-UI 2026-10-06,
   * session 2]. The tab stays. Provisional (Q-23): the delay before refetching (eventual consistency);
   * Provisional (Q-13): the view goes back to page 1 and an active search is re-run.
   */
  async function refreshLater(statuses: RequestStatus[]) {
    await new Promise((resolve) => setTimeout(resolve, refreshDelayMs));
    setView(null);
    setSelected([]);
    await reloadFirstPages(statuses);
    if (q) await showPage(tab, q, accessRequestsUrl(repoId, tab, q), []);
  }

  /** Source and destination lists of a move (no reset tab: a `reset` destination is not listed). */
  function touched(from: RequestStatus, to: HandleStatus): RequestStatus[] {
    return to === from || to === "reset" ? [from] : [from, to];
  }

  async function act(user: string, status: HandleStatus) {
    setError(null);
    const from = tab;
    const res = await handleAccessRequest(repoId, user, status);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    await refreshLater(touched(from, status));
  }

  async function actOnSelected(status: "accepted" | "rejected") {
    setError(null);
    const res = await batchAccessRequests(repoId, status, selected);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    // REV-9: per-item outcomes. Provisional (Q-13): how HF reports a failed item is unrecorded; the
    // failed items are listed verbatim.
    const failed = Array.isArray(res.data) ? res.data.filter((o) => !o.ok) : [];
    // Provisional (Q-13): like a row action, the current tab and the destination are refetched.
    await refreshLater(touched(tab, status));
    if (failed.length > 0) {
      setError({
        status: res.status,
        code: null,
        message: failed.map((o) => `${o.userId ?? o.user}: ${o.error ?? "failed"}`).join(", "),
      });
    }
  }

  function changeTab(next: RequestStatus) {
    setTab(next);
    setView(null); // back to the first page (Provisional (Q-13): HF's paging across tab switches is unrecorded)
    setSelected([]);
    // [OBS-UI 2026-10-06] switching to a tab refetches its list (a search re-runs on it instead).
    if (!q) void reloadFirstPages([next]);
  }

  function goTo(url: string, earlier: string[]) {
    void showPage(tab, q, url, earlier);
  }

  const allSelected = rows !== null && rows.length > 0 && rows.every((r) => selected.includes(r.user._id));

  return (
    <dialog ref={dialogRef} aria-labelledby="manage-access-title" className="dialog" onClose={onClose}>
      <h2 id="manage-access-title">Manage access requests</h2>
      {/* [OBS-UI 2026-10-06] an icon-only close button. */}
      <button type="button" aria-label="Close" onClick={() => dialogRef.current?.close()} className="dialog-close">
        <span aria-hidden="true">×</span>
      </button>
      <p>
        {REQUEST_TABS.map((status) => (
          // [OBS-UI 2026-10-06] plain buttons, no role="tab". aria-current marks the shown list
          // (HF marks it visually only).
          <button
            key={status}
            type="button"
            aria-current={tab === status ? "true" : undefined}
            onClick={() => changeTab(status)}
          >
            {/* Counts appear once the list is loaded. Provisional (Q-13): n = items on the first page. */}
            {firstPages[status] ? `${status} (${firstPages[status].items.length})` : status}
          </button>
        ))}
      </p>
      <p>
        <input
          type="search"
          placeholder="Search requests"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />{" "}
        {/* [OBS-UI 2026-10-06] "1 matching result". Provisional (Q-13): the plural form and n (items on
            the shown page) are guesses. */}
        {q && current && <span>{`${rows?.length ?? 0} matching result${rows?.length === 1 ? "" : "s"}`}</span>}
      </p>
      <p>
        <label>
          <input
            type="checkbox"
            checked={allSelected}
            onChange={(e) => setSelected(e.target.checked && rows ? rows.map((r) => r.user._id) : [])}
          />{" "}
          Select all
        </label>
        {selected.length > 0 && (
          <>
            {" "}
            <span>{selected.length} selected</span>{" "}
            <button type="button" onClick={() => void actOnSelected("accepted")}>
              Accept selected
            </button>{" "}
            <button type="button" onClick={() => void actOnSelected("rejected")}>
              Reject selected
            </button>
          </>
        )}
      </p>
      <ErrorNotice error={error} />
      {processing && <p>Processing...</p>}
      {/* [OBS-UI 2026-10-06] "No pending access requests", "No accepted access requests";
          Provisional (Q-13): "No rejected access requests" by analogy. */}
      {rows && rows.length === 0 && <p>No {tab} access requests</p>}
      {rows && rows.length > 0 && (
        <ul>
          {rows.map((req) => (
            <RequestRow
              key={req.user.user}
              req={req}
              actions={ROW_ACTIONS[tab]}
              selected={selected.includes(req.user._id)}
              onSelect={(on) =>
                setSelected((s) => (on ? [...s, req.user._id] : s.filter((id) => id !== req.user._id)))
              }
              onAction={(user, status) => void act(user, status)}
            />
          ))}
        </ul>
      )}
      <p>
        {/* [OBS-UI 2026-10-06] links `Previous` and `Next`. Next follows the list's `Link: rel="next"`;
            Previous returns to the page before. Provisional (Q-13): an unavailable link is rendered
            without href (disabled). */}
        <PageLink
          label="Previous"
          url={previous.at(-1) ?? null}
          onFollow={(url) => goTo(url, previous.slice(0, -1))}
        />{" "}
        <PageLink
          label="Next"
          url={page?.next ?? null}
          onFollow={(url) => page && goTo(url, [...previous, page.url])}
        />
      </p>
    </dialog>
  );
}

function PageLink({ label, url, onFollow }: { label: string; url: string | null; onFollow: (url: string) => void }) {
  if (!url) return <a aria-disabled="true">{label}</a>;
  return (
    <a
      href={url}
      onClick={(e) => {
        e.preventDefault();
        onFollow(url);
      }}
    >
      {label}
    </a>
  );
}

function RequestRow({
  req,
  actions,
  selected,
  onSelect,
  onAction,
}: {
  req: AccessRequest;
  actions: { label: string; status: HandleStatus }[];
  selected: boolean;
  onSelect: (on: boolean) => void;
  onAction: (user: string, status: HandleStatus) => void;
}) {
  const username = req.user.user;
  const fields = req.fields ? Object.entries(req.fields) : [];
  return (
    <li>
      {/* [OBS-UI 2026-10-06] row checkbox, value = the user's _id. */}
      <input
        type="checkbox"
        aria-label={`Select access request from ${username}`}
        value={req.user._id}
        checked={selected}
        onChange={(e) => onSelect(e.target.checked)}
      />{" "}
      {/* Row: username (link) · email · relative time of the request's `timestamp`, not `reviewedAt`
          [OBS-UI 2026-10-06]. Email is absent for granted users (REQ-5). */}
      <a href={`/${username}`}>{username}</a>
      {req.user.email ? <> · {req.user.email}</> : null} ·{" "}
      <time dateTime={req.timestamp}>{relativeTime(req.timestamp)}</time>{" "}
      {actions.map((a) => (
        <button key={a.label} type="button" onClick={() => onAction(username, a.status)}>
          {a.label}
        </button>
      ))}
      {fields.length > 0 && (
        // Provisional (Q-13): how HF displays the form answers is unrecorded; label → value list.
        <dl>
          {fields.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </li>
  );
}

function relativeTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : formatDistanceToNow(date, { addSuffix: true });
}
