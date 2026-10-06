// Server-component access to the backend, as the persona and backend chosen by cookie.
import { cookies } from "next/headers";
import { BACKEND_COOKIE, parseBackend, type BackendId } from "./backends";
import { backendUrlFor } from "./config";
import { deriveGateState, type GateState } from "./gateState";
import { readBackendError, toApiResult, type ApiResult } from "./httpError";
import { authHeaders, parsePersona, PERSONA_COOKIE, type PersonaId } from "./personas";

export async function currentPersona(): Promise<PersonaId> {
  const store = await cookies();
  return parsePersona(store.get(PERSONA_COOKIE)?.value);
}

export async function currentBackend(): Promise<BackendId> {
  const store = await cookies();
  return parseBackend(store.get(BACKEND_COOKIE)?.value);
}

export async function currentBackendUrl(): Promise<string> {
  return backendUrlFor(await currentBackend());
}

export async function backendFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const persona = await currentPersona();
  return fetch(`${await currentBackendUrl()}${path}`, {
    ...init,
    headers: { ...authHeaders(persona), ...(init.headers as Record<string, string> | undefined) },
    redirect: "manual",
    cache: "no-store",
  });
}

export async function backendJson<T>(path: string): Promise<ApiResult<T>> {
  try {
    return await toApiResult<T>(await backendFetch(path));
  } catch (err) {
    const url = await currentBackendUrl();
    return { ok: false, error: { status: 502, code: null, message: `Backend unreachable at ${url}: ${String(err)}` } };
  }
}

/** `/api/models/{ns}/{name}` style prefix with each segment encoded. */
export function repoPath(ns: string, name: string): string {
  return `${encodeURIComponent(ns)}/${encodeURIComponent(name)}`;
}

/** Requester gate state of `repo` (an encoded `repoPath`) for the current persona, from auth-check (lib/gateState). */
export async function fetchGateState(repo: string): Promise<GateState> {
  try {
    const res = await backendFetch(`/api/models/${repo}/auth-check`);
    if (res.status === 200) return deriveGateState({ status: 200, code: null, message: "" });
    return deriveGateState(await readBackendError(res));
  } catch (err) {
    return { kind: "unmapped", status: 502, code: null, message: `Backend unreachable: ${String(err)}` };
  }
}

export interface WhoAmI {
  name?: string;
  fullname?: string;
  orgs?: { name?: string }[];
}
