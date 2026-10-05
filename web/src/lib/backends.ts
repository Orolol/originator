// Backends the web app can talk to (docs/system.md): both speak HF's wire protocol, so the switch
// only changes the base URL. Chosen per browser by cookie, like the persona. Shared by server and
// client code; the URLs themselves are server-only (lib/config.ts).

export const BACKEND_COOKIE = "backend";

export const BACKENDS = {
  clone: { note: "in-memory replica, local and resettable" },
  bridge: { note: "live huggingface.co: writes reach the real Hub" },
} as const;

export type BackendId = keyof typeof BACKENDS;

export const BACKEND_IDS = Object.keys(BACKENDS) as BackendId[];

/** The clone by default, so that nothing reaches the real Hub unless the bridge is chosen explicitly. */
export const DEFAULT_BACKEND: BackendId = "clone";

export function isBackendId(value: unknown): value is BackendId {
  return typeof value === "string" && Object.hasOwn(BACKENDS, value);
}

/** Unknown or missing cookie values fall back to the default backend. */
export function parseBackend(value: string | undefined | null): BackendId {
  return isBackendId(value) ? value : DEFAULT_BACKEND;
}
