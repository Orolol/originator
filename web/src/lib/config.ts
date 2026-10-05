// Server-only configuration. The web app never knows whether it talks to the bridge or the clone
// (docs/system.md): it only knows BACKEND_URL.

export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8100").replace(/\/+$/, "");

/** Repo linked from the index page (the bridge only allows its sandbox repo). */
export const SANDBOX_REPO = process.env.SANDBOX_REPO ?? "Orosius/deltanet-mla-latent";
