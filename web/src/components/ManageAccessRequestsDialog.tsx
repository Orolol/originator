"use client";
// Owner modal "Manage access requests" (docs/hf-gated/ui.md §C). Lists and actions are owned by
// GatedUserAccess; this component only renders them and reports clicks.
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import type { BackendError } from "@/lib/httpError";
import type { AccessRequest, HandleStatus, RequestStatus } from "@/lib/hubClient";
import { ErrorNotice } from "./ErrorNotice";

export const REQUEST_TABS: RequestStatus[] = ["pending", "accepted", "rejected"];

export type RequestLists = Record<RequestStatus, AccessRequest[] | null>;

// Provisional (Q-13): no `reset` tab (unknown whether the UI has one; the API has a reset list).
const ROW_ACTIONS: Record<RequestStatus, { label: string; status: HandleStatus }[]> = {
  pending: [
    { label: "Accept", status: "accepted" }, // [DOC] [DOC-IMG]
    { label: "Reject", status: "rejected" }, // [DOC] [DOC-IMG]; Provisional (Q-13): no rejection-reason input
  ],
  accepted: [
    { label: "Reject", status: "rejected" }, // [DOC]
    { label: "Cancel", status: "pending" }, // [DOC] back to pending (REV-4)
  ],
  // Provisional (Q-13): rejected-tab actions are unrecorded; the API allows → accepted and → pending.
  rejected: [
    { label: "Accept", status: "accepted" },
    { label: "Cancel", status: "pending" },
  ],
};

interface Props {
  lists: RequestLists;
  error: BackendError | null;
  onAction: (user: string, status: HandleStatus) => void;
  onClose: () => void;
}

export function ManageAccessRequestsDialog({ lists, error, onAction, onClose }: Props) {
  const [tab, setTab] = useState<RequestStatus>("pending");
  const rows = lists[tab];
  return (
    <div className="backdrop">
      <div role="dialog" aria-modal="true" aria-labelledby="manage-access-title" className="dialog">
        <h2 id="manage-access-title">Manage access requests</h2>
        <button type="button" aria-label="Close" onClick={onClose} className="dialog-close">
          ×
        </button>
        <div role="tablist">
          {REQUEST_TABS.map((status) => (
            <button
              key={status}
              type="button"
              role="tab"
              id={`tab-${status}`}
              aria-controls={`tabpanel-${status}`}
              aria-selected={tab === status}
              onClick={() => setTab(status)}
            >
              {/* Counts appear once the list is loaded. */}
              {lists[status] ? `${status} (${lists[status].length})` : status}
            </button>
          ))}
        </div>
        <ErrorNotice error={error} />
        <div role="tabpanel" id={`tabpanel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {rows && (
            <ul>
              {rows.map((req) => (
                <RequestRow key={req.user.user} req={req} actions={ROW_ACTIONS[tab]} onAction={onAction} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function RequestRow({
  req,
  actions,
  onAction,
}: {
  req: AccessRequest;
  actions: { label: string; status: HandleStatus }[];
  onAction: (user: string, status: HandleStatus) => void;
}) {
  const username = req.user.user;
  const fields = req.fields ? Object.entries(req.fields) : [];
  return (
    <li>
      {/* Row: username (link) · email · relative time (ui.md §C). Email is absent for granted users (REQ-5). */}
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
