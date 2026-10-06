"use client";
// Owner settings section "Gated user access" (docs/hf-gated/ui.md §B1–B3; side effects §D).
// Provisional (Q-12): every control saves immediately (one PUT per change, no save button, no
// confirmation on disable); a failed save shows the backend error and keeps the previous value.
import { useState } from "react";
import type { BackendError } from "@/lib/httpError";
import {
  accessRequestsUrl,
  fetchAccessRequestPage,
  grantAccess,
  updateRepoSettings,
  userAccessReportUrl,
  type Gated,
  type NotificationsMode,
  type RepoSettingsUpdate,
} from "@/lib/hubClient";
import { AddAccessDialog } from "./AddAccessDialog";
import { ErrorNotice } from "./ErrorNotice";
import { ManageAccessRequestsDialog } from "./ManageAccessRequestsDialog";

// Provisional (Q-23, Q-13): the real Hub is eventually consistent (~1 s, the client tests sleep 1 s),
// and HF's refresh behaviour after an action is unrecorded: we refetch the lists after this delay.
export const REFRESH_DELAY_MS = 1000;

interface Props {
  repoId: string;
  initialGated: Gated;
  /** Pending requests at page load; null when the list could not be read (e.g. repo not gated). */
  initialPendingCount: number | null;
  refreshDelayMs?: number;
}

export function GatedUserAccess({ repoId, initialGated, initialPendingCount, refreshDelayMs = REFRESH_DELAY_MS }: Props) {
  const [gated, setGated] = useState<Gated>(initialGated);
  const [pendingCount, setPendingCount] = useState<number | null>(initialPendingCount);
  // Provisional (Q-12): notification settings are write-only through the API (CFG-3), so the
  // current values cannot be read. We start from "Once a day" (the doc screenshot) and an empty
  // email, then show what the last successful PUT echoed.
  const [notificationsMode, setNotificationsMode] = useState<NotificationsMode>("bulk");
  const [email, setEmail] = useState("");
  const [savedEmail, setSavedEmail] = useState("");
  const [settingsError, setSettingsError] = useState<BackendError | null>(null);

  const [reviewOpen, setReviewOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [grantError, setGrantError] = useState<BackendError | null>(null);

  async function save(body: RepoSettingsUpdate): Promise<RepoSettingsUpdate | null> {
    setSettingsError(null);
    const res = await updateRepoSettings(repoId, body);
    if (!res.ok) {
      setSettingsError(res.error);
      return null;
    }
    // CFG-3: the response echoes only the fields sent.
    return res.data && typeof res.data === "object" ? res.data : {};
  }

  async function changeGated(next: Gated) {
    const echo = await save({ gated: next });
    if (echo) setGated(echo.gated !== undefined ? echo.gated : next);
  }

  async function changeNotificationsMode(next: NotificationsMode) {
    const echo = await save({ gatedNotificationsMode: next });
    if (echo) setNotificationsMode(echo.gatedNotificationsMode ?? next);
  }

  async function saveEmail() {
    if (email === savedEmail) return;
    const echo = await save({ gatedNotificationsEmail: email });
    if (echo) {
      const value = echo.gatedNotificationsEmail ?? email;
      setSavedEmail(value);
      setEmail(value);
    }
  }

  async function grant(user: string) {
    setGrantError(null);
    const res = await grantAccess(repoId, user);
    if (!res.ok) {
      setGrantError(res.error);
      return;
    }
    // Provisional (Q-12): after a grant the dialog closes and, after the refresh delay, the pending
    // count is reread (a pending user who is granted leaves that list).
    setAddOpen(false);
    await new Promise((resolve) => setTimeout(resolve, refreshDelayMs));
    const pending = await fetchAccessRequestPage(accessRequestsUrl(repoId, "pending"));
    if (pending.ok) setPendingCount(pending.data.items.length);
  }

  return (
    <section aria-labelledby="gated-user-access-title">
      <h2 id="gated-user-access-title">Gated user access</h2>
      <p>
        Access requests are currently <strong>{gated ? "enabled" : "disabled"}</strong> for this model.
      </p>
      <p>
        When enabled, users must share their contact information (email and username) and agree to your terms and
        conditions (if any) in order to access this model. You can download the list of users who have accepted and
        had access at any time.
      </p>
      {gated ? (
        <button type="button" onClick={() => changeGated(false)}>
          Disable Access requests
        </button>
      ) : (
        // CFG-1: enabling from the UI starts in automatic approval.
        <button type="button" onClick={() => changeGated("auto")}>
          Enable Access requests
        </button>
      )}
      <ErrorNotice error={settingsError} />

      {gated && (
        <>
          {/* Control order follows the doc screenshots (ui.md B2/B3): one row with the mode select,
              review, report and (manual) Add access; then a notifications row in manual mode. */}
          <p>
            <label htmlFor="gated-new-requests">New requests:</label>{" "}
            <select
              id="gated-new-requests"
              value={gated}
              onChange={(e) => changeGated(e.target.value as Gated)}
            >
              <option value="auto">Automatic approval</option>
              <option value="manual">Manual review</option>
            </select>{" "}
            {/* [OBS-UI 2026-10-06] N = the pending count, no number until it is known. Ours is known at
                page load (server-side list read); HF's appears after a client-side load. */}
            <button type="button" onClick={() => setReviewOpen(true)}>
              {pendingCount === null ? "Review access requests" : `Review access requests (${pendingCount})`}
            </button>{" "}
            {/* REP-1: browser download of GET /{repo}/user-access-report. */}
            <button type="button" onClick={() => window.location.assign(userAccessReportUrl(repoId))}>
              Download user access report
            </button>
            {gated === "manual" && (
              <>
                {" "}
                <button type="button" onClick={() => setAddOpen(true)}>
                  Add access
                </button>
              </>
            )}
          </p>

          {gated === "manual" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void saveEmail();
              }}
            >
              <label htmlFor="gated-notifications-mode">Notifications frequency</label>{" "}
              <select
                id="gated-notifications-mode"
                value={notificationsMode}
                onChange={(e) => changeNotificationsMode(e.target.value as NotificationsMode)}
              >
                <option value="bulk">Once a day</option>
                {/* [OBS-UI 2026-10-06] options bulk = "Once a day", real-time = "Real-time". */}
                <option value="real-time">Real-time</option>
              </select>{" "}
              {/* [OBS-UI 2026-10-06] type="email", so the browser validates it (and blocks Enter on an
                  invalid address). Provisional (Q-12): saved on Enter or when the field loses focus;
                  empty → default recipients; the backend's answer is shown. */}
              <label htmlFor="gated-notifications-email">Notifications email</label>{" "}
              <input
                id="gated-notifications-email"
                type="email"
                placeholder="example@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => void saveEmail()}
              />
            </form>
          )}
        </>
      )}

      {reviewOpen && (
        <ManageAccessRequestsDialog
          repoId={repoId}
          refreshDelayMs={refreshDelayMs}
          onPendingCount={setPendingCount}
          onClose={() => setReviewOpen(false)}
        />
      )}
      {addOpen && (
        <AddAccessDialog
          error={grantError}
          onGrant={(user) => void grant(user)}
          onClose={() => {
            setAddOpen(false);
            setGrantError(null);
          }}
        />
      )}
    </section>
  );
}
