"use client";
// Table of `/settings/gated-repos` [OBS-UI 2026-10-06]: sortable header buttons `Repo Name`, `Type`,
// `Date`, `Request Status`; one row per request (repo link, `model`, date, status in uppercase) and,
// on rows the API lets the user withdraw, an icon-only button titled "Cancel this access request".
// Session 2: the button asks a native confirm(), then sends `POST …/user-access-request/cancel` (no
// body) and the row disappears without a page reload.
import { useState } from "react";
import type { GatedRepoRow } from "@/lib/gatedRepos";
import type { BackendError } from "@/lib/httpError";
import { cancelAccessRequest } from "@/lib/hubClient";
import { ErrorNotice } from "./ErrorNotice";

type SortKey = "repo" | "type" | "date" | "status";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "repo", label: "Repo Name" },
  { key: "type", label: "Type" },
  { key: "date", label: "Date" },
  { key: "status", label: "Request Status" },
];

export const CONFIRM_CANCEL = "Are you sure you want to cancel this access request?";

export function GatedReposTable({ rows }: { rows: GatedRepoRow[] }) {
  // Provisional (Q-3): HF's default order and sort directions are unrecorded (one row was seen). Rows
  // keep the server order until a header is clicked; a click sorts ascending, a second click descending.
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 } | null>(null);
  const [cancelled, setCancelled] = useState<string[]>([]);
  const [error, setError] = useState<BackendError | null>(null);
  const shown = rows.filter((r) => !cancelled.includes(r.repo));
  const sorted = sort
    ? [...shown].sort((a, b) => sort.dir * String(a[sort.key] ?? "").localeCompare(String(b[sort.key] ?? "")))
    : shown;

  async function cancel(repo: string) {
    if (!window.confirm(CONFIRM_CANCEL)) return;
    setError(null);
    const res = await cancelAccessRequest(repo);
    // Provisional (Q-3): how HF reports a failed cancel is unrecorded; the backend error is shown verbatim.
    if (!res.ok) setError(res.error);
    else setCancelled((c) => [...c, repo]);
  }

  return (
    <>
      <ErrorNotice error={error} />
      <table>
        <thead>
          <tr>
            {COLUMNS.map(({ key, label }) => (
              <th key={key}>
                <button
                  type="button"
                  onClick={() => setSort((s) => ({ key, dir: s?.key === key && s.dir === 1 ? -1 : 1 }))}
                >
                  {label}
                </button>
              </th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={row.repo}>
              <td>
                <a href={`/${row.repo}`}>{row.repo}</a>
              </td>
              <td>{row.type}</td>
              {/* Provisional (Q-3): the submission date is not available through the API. */}
              <td>{row.date ?? ""}</td>
              <td>{row.status.toUpperCase()}</td>
              <td>
                {/* REQ-7: only a pending request can be withdrawn, so only pending rows get the button. */}
                {row.status === "pending" && (
                  <button
                    type="button"
                    title="Cancel this access request"
                    aria-label="Cancel this access request"
                    onClick={() => void cancel(row.repo)}
                  >
                    <span aria-hidden="true">✕</span>
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
