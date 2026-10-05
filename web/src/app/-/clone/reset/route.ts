// `POST /-/clone/reset` (form field `next`): restores the clone's default seed through its control
// endpoint `POST /__clone__/reset` (docs/system.md "Clone"), then redirects back. Web-app-only control
// route. Only when the browser's backend is the clone and nothing is pinned: never aimed at the bridge.
import { NextResponse, type NextRequest } from "next/server";
import { BACKEND_COOKIE, parseBackend } from "@/lib/backends";
import { BACKEND_URLS, pinnedBackendUrl } from "@/lib/config";
import { safeNext } from "@/lib/safeNext";

export const dynamic = "force-dynamic";

function plain(status: number, text: string): Response {
  return new Response(text, { status, headers: { "content-type": "text/plain; charset=utf-8" } });
}

export async function POST(req: NextRequest) {
  if (pinnedBackendUrl()) {
    return plain(409, `Backend pinned by BACKEND_URL=${pinnedBackendUrl()}; reset it through its own control endpoint.`);
  }
  if (parseBackend(req.cookies.get(BACKEND_COOKIE)?.value) !== "clone") {
    return plain(409, "Reset is only available when the backend is the clone.");
  }
  const form = await req.formData().catch(() => null);
  const next = safeNext(typeof form?.get("next") === "string" ? (form.get("next") as string) : null);
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URLS.clone}/__clone__/reset`, { method: "POST", cache: "no-store" });
  } catch (err) {
    return plain(502, `Clone unreachable at ${BACKEND_URLS.clone}: ${String(err)}`);
  }
  if (!upstream.ok) {
    return plain(502, `Clone reset failed: ${upstream.status} ${await upstream.text()}`);
  }
  return NextResponse.redirect(new URL(next, req.nextUrl.origin), 303);
}
