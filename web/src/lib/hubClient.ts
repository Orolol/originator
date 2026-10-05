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
    _id?: string;
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

/** REV-10: one list per status (no query: default limit 1000, one page). */
export function listAccessRequests(repoId: string, status: RequestStatus) {
  return jsonRequest<AccessRequest[]>("GET", `${modelApi(repoId)}/user-access-request/${status}`);
}

/** REV-5 / §5.1: `{user, status}` by username. No rejectionReason input in our UI (Q-13). */
export function handleAccessRequest(repoId: string, user: string, status: HandleStatus) {
  return jsonRequest<unknown>("POST", `${modelApi(repoId)}/user-access-request/handle`, { user, status });
}

/** REV-6: `POST …/grant {user}`. */
export function grantAccess(repoId: string, user: string) {
  return jsonRequest<unknown>("POST", `${modelApi(repoId)}/user-access-request/grant`, { user });
}

/** "Add access" user search (docs/system.md backend surface). */
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
