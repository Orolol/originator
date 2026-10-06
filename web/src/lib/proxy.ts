// Web-route → backend proxy (docs/system.md "Web app conventions": the browser fires HF-shaped
// requests at the web origin, the web server forwards them to the chosen backend with the persona token).
import type { NextRequest } from "next/server";
import { BACKEND_COOKIE, parseBackend } from "./backends";
import { backendUrlFor } from "./config";
import { authHeaders, parsePersona, PERSONA_COOKIE, type PersonaId } from "./personas";

/** Response headers passed back to the browser (docs/system.md "Backend surface"). Never Set-Cookie. */
export const PASSTHROUGH_HEADERS = [
  "content-type",
  "content-disposition",
  "x-error-code",
  "x-error-message",
  "www-authenticate",
  "link",
  "location",
  "x-total-count",
  "x-repo-commit",
  "etag",
] as const;

export function personaFromRequest(req: NextRequest): PersonaId {
  return parsePersona(req.cookies.get(PERSONA_COOKIE)?.value);
}

/** Base URL of the backend this browser chose (cookie), unless BACKEND_URL pins one. */
export function backendUrlFromRequest(req: NextRequest): string {
  return backendUrlFor(parseBackend(req.cookies.get(BACKEND_COOKIE)?.value));
}

/**
 * Absolute backend URLs in `Location` / `Link` (the bridge already rewrote huggingface.co to its
 * own URL) are mapped to the web origin, so redirects and pagination stay on the web app.
 * Web-side normalisation, the analogue of the bridge's rule; other hosts (CDN) are untouched.
 */
export function rewriteBackendUrls(value: string, backendUrl: string, webOrigin: string): string {
  return value.split(backendUrl).join(webOrigin);
}

interface ForwardOptions {
  method?: string;
  body?: BodyInit;
  contentType?: string;
  /** Query string sent upstream (with its `?`); the incoming one by default. */
  search?: string;
}

/** One upstream call per incoming call; no redirect following (the browser sees 3xx as is). */
export async function callBackend(req: NextRequest, path: string, opts: ForwardOptions = {}): Promise<Response> {
  const method = opts.method ?? req.method;
  const headers: Record<string, string> = { ...authHeaders(personaFromRequest(req)) };
  let body: BodyInit | undefined = opts.body;
  if (body !== undefined) {
    if (opts.contentType) headers["Content-Type"] = opts.contentType;
  } else if (method !== "GET" && method !== "HEAD") {
    const buf = await req.arrayBuffer();
    if (buf.byteLength > 0) body = buf;
    const ct = req.headers.get("content-type");
    if (ct) headers["Content-Type"] = ct;
  }
  return fetch(`${backendUrlFromRequest(req)}${path}${opts.search ?? req.nextUrl.search}`, {
    method,
    headers,
    body,
    redirect: "manual",
    cache: "no-store",
  });
}

/** Relays status, body and the allow-listed headers of a backend response. */
export function relay(upstream: Response, req: NextRequest): Response {
  const headers = new Headers();
  for (const name of PASSTHROUGH_HEADERS) {
    const value = upstream.headers.get(name);
    if (value === null) continue;
    headers.set(
      name,
      name === "location" || name === "link"
        ? rewriteBackendUrls(value, backendUrlFromRequest(req), req.nextUrl.origin)
        : value,
    );
  }
  const noBody = req.method === "HEAD" || [101, 204, 205, 304].includes(upstream.status);
  return new Response(noBody ? null : upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}

/** Proxies the request to the same path on the backend (path and query verbatim). */
export async function forward(req: NextRequest): Promise<Response> {
  try {
    return relay(await callBackend(req, req.nextUrl.pathname), req);
  } catch (err) {
    return backendUnreachable(req, err);
  }
}

export function backendUnreachable(req: NextRequest, err: unknown): Response {
  // Web-app-only failure (no HF equivalent): the backend did not answer at all.
  return new Response(`Backend unreachable at ${backendUrlFromRequest(req)}: ${String(err)}`, {
    status: 502,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
