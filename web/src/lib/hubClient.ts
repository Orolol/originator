// Browser-side calls, fired at the web origin with HF's paths and payloads (docs/system.md "Same
// requests fired"; side-effect matrix in docs/hf-gated/ui.md §D). The web server proxies them.
import { toApiResult, type ApiResult } from "./httpError";

export type Gated = false | "auto" | "manual";
export type RequestStatus = "pending" | "accepted" | "rejected";
export type HandleStatus = "pending" | "accepted" | "rejected" | "reset";
export type NotificationsMode = "bulk" | "real-time";

export interface RepoSettingsUpdate {
  gated?: Gated;
  gatedNotificationsMode?: NotificationsMode;
  gatedNotificationsEmail?: string;
}

/** List item of `GET …/user-access-request/{status}` (api.md §2). */
export interface AccessRequest {
  user: {
    _id: string;
    user: string;
    fullname?: string;
    avatarUrl?: string;
    email?: string | null;
  };
  status: string;
  timestamp: string;
  reviewedAt?: string;
  fields?: Record<string, string>;
}

export interface QuickSearchUser {
  user: string;
  fullname?: string;
}

/** One page of an owner list, with the `Link: <…>; rel="next"` target (REV-10), as a web-origin path. */
export interface AccessRequestPage {
  url: string;
  items: AccessRequest[];
  next: string | null;
}

/** Item of the `batch` response (REV-9, api.md §1). */
export interface BatchOutcome {
  user?: string;
  userId?: string;
  ok: boolean;
  error?: string;
}

function modelApi(repoId: string): string {
  return `/api/models/${repoId}`;
}

async function jsonRequest<T>(method: string, url: string, body?: unknown): Promise<ApiResult<T>> {
  const init: RequestInit = { method };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  try {
    return await toApiResult<T>(await fetch(url, init));
  } catch (err) {
    return { ok: false, error: { status: 0, code: null, message: String(err) } };
  }
}

/** CFG-2/CFG-3: `PUT /api/models/{repo}/settings`; the response echoes only the fields sent. */
export function updateRepoSettings(repoId: string, body: RepoSettingsUpdate) {
  return jsonRequest<RepoSettingsUpdate>("PUT", `${modelApi(repoId)}/settings`, body);
}

/** HF's review modal asks for 100 items per page [OBS-UI 2026-10-06]. */
export const LIST_LIMIT = 100;

/**
 * REV-10 list URL as HF's modal builds it [OBS-UI 2026-10-06]: `…/{status}?limit=100`, plus `&q=` for a
 * search (current tab only).
 */
export function accessRequestsUrl(repoId: string, status: RequestStatus, q = ""): string {
  const params = new URLSearchParams({ limit: String(LIST_LIMIT) });
  if (q) params.set("q", q);
  return `${modelApi(repoId)}/user-access-request/${status}?${params}`;
}

/**
 * Target of `Link: <…>; rel="next"` (REV-10), reduced to its path and query so that it is fetched
 * through the web `/api` proxy whatever host the backend wrote (the proxy already maps the backend's
 * own URL to the web origin). Anything outside `/api/` is ignored.
 */
export function nextPageUrl(link: string | null): string | null {
  const match = link?.match(/<([^>]*)>\s*;\s*rel="?next"?/);
  if (!match) return null;
  try {
    const url = new URL(match[1], "http://web.invalid");
    return url.pathname.startsWith("/api/") ? `${url.pathname}${url.search}` : null;
  } catch {
    return null;
  }
}

/** One page of an owner list (`url` from `accessRequestsUrl` or a previous page's `next`). */
export async function fetchAccessRequestPage(url: string): Promise<ApiResult<AccessRequestPage>> {
  let res: Response;
  try {
    res = await fetch(url);
  } catch (err) {
    return { ok: false, error: { status: 0, code: null, message: String(err) } };
  }
  const next = nextPageUrl(res.headers.get("link"));
  const result = await toApiResult<unknown>(res);
  if (!result.ok) return result;
  const items = Array.isArray(result.data) ? (result.data as AccessRequest[]) : [];
  return { ok: true, status: result.status, data: { url, items, next } };
}

/**
 * REV-5 / §5.1: `{user, status}` by username. No rejectionReason input in our UI (Q-13).
 * Provisional (Q-13): HF's own modal sends `{"status", "userId": <_id>}` [OBS-UI 2026-10-06, session 2];
 * we keep `{user, status}`, the body of the recorded live walkthrough our clone run is diffed against.
 */
export function handleAccessRequest(repoId: string, user: string, status: HandleStatus) {
  return jsonRequest<unknown>("POST", `${modelApi(repoId)}/user-access-request/handle`, { user, status });
}

/**
 * REV-9: `POST …/batch {status, requests: [{userId}]}`, the user `_id`s being the values of the
 * modal's row checkboxes [OBS-UI 2026-10-06]. Provisional (Q-13): what HF's "Accept selected" /
 * "Reject selected" send was not recorded (not clicked); this is the API's documented shape.
 */
export function batchAccessRequests(repoId: string, status: "accepted" | "rejected", userIds: string[]) {
  return jsonRequest<BatchOutcome[]>("POST", `${modelApi(repoId)}/user-access-request/batch`, {
    status,
    requests: userIds.map((userId) => ({ userId })),
  });
}

/**
 * Requester self-cancel (REQ-7): `POST …/user-access-request/cancel` with no body, fired by the browser
 * from `/settings/gated-repos` like HF's page does [OBS-UI 2026-10-06, session 2].
 */
export function cancelAccessRequest(repoId: string) {
  return jsonRequest<unknown>("POST", `${modelApi(repoId)}/user-access-request/cancel`);
}

/** REV-6: `POST …/grant {user}`. */
export function grantAccess(repoId: string, user: string) {
  return jsonRequest<unknown>("POST", `${modelApi(repoId)}/user-access-request/grant`, { user });
}

/**
 * "Add access" user search: `GET /api/quicksearch?q=<text>&type=user`, with `q=` empty when the dialog
 * opens [OBS-UI 2026-10-06] (Q-25).
 */
export async function searchUsers(q: string): Promise<ApiResult<QuickSearchUser[]>> {
  const res = await jsonRequest<{ users?: unknown }>("GET", `/api/quicksearch?q=${encodeURIComponent(q)}&type=user`);
  if (!res.ok) return res;
  const raw = Array.isArray(res.data?.users) ? (res.data.users as Record<string, unknown>[]) : [];
  const users = raw.flatMap((u) =>
    typeof u.user === "string" ? [{ user: u.user, fullname: typeof u.fullname === "string" ? u.fullname : undefined }] : [],
  );
  return { ok: true, status: res.status, data: users };
}

export function userAccessReportUrl(repoId: string): string {
  return `/${repoId}/user-access-report`;
}
