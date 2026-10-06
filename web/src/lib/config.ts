// Server-only configuration. The web app never knows *how* a backend works (docs/system.md): it only
// knows each backend's base URL, and which one the browser chose (lib/backends.ts).
import type { BackendId } from "./backends";

function trimUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

export const BACKEND_URLS: Record<BackendId, string> = {
  clone: trimUrl(process.env.CLONE_URL ?? "http://127.0.0.1:8200"),
  bridge: trimUrl(process.env.BRIDGE_URL ?? "http://127.0.0.1:8100"),
};

/**
 * `BACKEND_URL`, when set, pins every request to that URL and disables the switch. The e2e configs
 * rely on it: the clone walkthrough (which writes) must never be redirected to the bridge.
 * Read at call time so tests can set it.
 */
export function pinnedBackendUrl(): string | null {
  return process.env.BACKEND_URL ? trimUrl(process.env.BACKEND_URL) : null;
}

export function backendUrlFor(backend: BackendId): string {
  return pinnedBackendUrl() ?? BACKEND_URLS[backend];
}

/**
 * Repo linked from the index page, per backend: the bridge only allows its live sandbox repo, the
 * clone serves its seeded copy of the repo recorded on 2026-10-05. `SANDBOX_REPO` overrides both.
 */
const SANDBOX_REPOS: Record<BackendId, string> = {
  clone: "Orosius/deltanet-mla-latent",
  bridge: "OwnerOfTheGatedModel/tiny-gated-model",
};

export function sandboxRepoFor(backend: BackendId): string {
  return process.env.SANDBOX_REPO ?? SANDBOX_REPOS[backend];
}
