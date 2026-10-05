// `GET /-/persona?as=<persona>&next=<path>`: sets the persona cookie and redirects (docs/system.md
// "Web app conventions"). Web-app-only control route, not part of HF's surface.
import { NextResponse, type NextRequest } from "next/server";
import { isPersonaId, PERSONA_COOKIE, PERSONA_IDS } from "@/lib/personas";
import { safeNext } from "@/lib/safeNext";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  const persona = req.nextUrl.searchParams.get("as");
  if (!isPersonaId(persona)) {
    return new Response(`Unknown persona ${JSON.stringify(persona)}; expected one of: ${PERSONA_IDS.join(", ")}`, {
      status: 400,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  const res = NextResponse.redirect(new URL(safeNext(req.nextUrl.searchParams.get("next")), req.nextUrl.origin), 303);
  res.cookies.set(PERSONA_COOKIE, persona, { path: "/", sameSite: "lax", httpOnly: true });
  return res;
}
