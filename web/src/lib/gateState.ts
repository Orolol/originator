// Requester gate state, derived from `GET /api/models/{repo}/auth-check` (docs/system.md
// "Requester gate state comes from auth-check"): the API has no "my request status" endpoint, so
// the gate box is chosen from the content-route answer (api.md §3.1). This is the ONLY place that
// maps auth-check answers to screens A1–A6 (docs/hf-gated/ui.md).

import type { BackendError } from "./httpError";

export type GateState =
  /** 200: the caller can read files. Owner bypass (ACC-1) and an accepted request (A4) look the same. */
  | { kind: "access" }
  /** 401 GatedRepo: anonymous visitor (A1, ACC-3, REQ-1). */
  | { kind: "anonymous"; message: string }
  /** 403 GatedRepo "…not in the authorized list…": logged in, no request (A2). */
  | { kind: "no-request"; message: string }
  /** 403 GatedRepo "…awaiting a review from the repo authors.": pending (A3). */
  | { kind: "pending"; message: string }
  /** 403 GatedRepo "…has been rejected by the repo's authors.": rejected (A5) [OBS 2026-10-05, Q-8]. */
  | { kind: "rejected"; message: string }
  /** 403 GatedRepo "…has been reset by the repo's authors. Visit … to submit a new request.": reset (A6) [OBS 2026-10-05]. */
  | { kind: "reset"; message: string }
  /** Anything else: shown verbatim, never guessed. */
  | { kind: "unmapped"; status: number; code: string | null; message: string };

const NOT_IN_AUTHORIZED_LIST = "you are not in the authorized list";
const AWAITING_REVIEW = "is awaiting a review from the repo authors";
const REJECTED = "has been rejected by the repo's authors";
const RESET = "has been reset by the repo's authors";

export function deriveGateState(authCheck: BackendError): GateState {
  const { status, code, message } = authCheck;
  if (status === 200) return { kind: "access" };
  if (code === "GatedRepo") {
    if (status === 401) return { kind: "anonymous", message };
    if (status === 403 && message.includes(NOT_IN_AUTHORIZED_LIST)) return { kind: "no-request", message };
    if (status === 403 && message.includes(AWAITING_REVIEW)) return { kind: "pending", message };
    if (status === 403 && message.includes(REJECTED)) return { kind: "rejected", message };
    if (status === 403 && message.includes(RESET)) return { kind: "reset", message };
  }
  return { kind: "unmapped", status, code, message };
}

/** A row status on `/settings/gated-repos` (HF shows it uppercase, e.g. `PENDING` [OBS-UI 2026-10-06]). */
export type GatedRepoRequestStatus = "pending" | "rejected" | "reset";

/**
 * `/settings/gated-repos` row for one repo, from the same auth-check answer. HF fills that page from
 * server props (`gatedReposRequests`); the API has no "my requests" endpoint, so we derive it.
 * No request / anonymous → no row; 200 → no row, because an accepted request and the owner bypass
 * (ACC-1) give the same answer. Provisional (Q-3): only `pending` was seen in HF's table; rejected
 * and reset requests are assumed to be listed too.
 */
export function gatedRepoRequestStatus(state: GateState): GatedRepoRequestStatus | null {
  switch (state.kind) {
    case "pending":
    case "rejected":
    case "reset":
      return state.kind;
    default:
      return null;
  }
}
