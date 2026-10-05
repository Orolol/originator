// `GET /-/backend?to=<clone|bridge>&next=<path>`: sets the backend cookie and redirects, like the
// persona switch (docs/system.md "Web app conventions"). Web-app-only control route.
import { NextResponse, type NextRequest } from "next/server";
import { BACKEND_COOKIE, BACKEND_IDS, isBackendId } from "@/lib/backends";
import { pinnedBackendUrl } from "@/lib/config";
import { safeNext } from "@/lib/safeNext";

export const dynamic = "force-dynamic";

function plain(status: number, text: string): Response {
  return new Response(text, { status, headers: { "content-type": "text/plain; charset=utf-8" } });
}

export function GET(req: NextRequest) {
  const pinned = pinnedBackendUrl();
  if (pinned) {
    // Fail loudly: a pinned run (e.g. the clone e2e, which writes) must never be switched.
    return plain(409, `Backend pinned by BACKEND_URL=${pinned}; the switch is disabled.`);
  }
  const backend = req.nextUrl.searchParams.get("to");
  if (!isBackendId(backend)) {
    return plain(400, `Unknown backend ${JSON.stringify(backend)}; expected one of: ${BACKEND_IDS.join(", ")}`);
  }
  const res = NextResponse.redirect(new URL(safeNext(req.nextUrl.searchParams.get("next")), req.nextUrl.origin), 303);
  res.cookies.set(BACKEND_COOKIE, backend, { path: "/", sameSite: "lax", httpOnly: true });
  return res;
}
