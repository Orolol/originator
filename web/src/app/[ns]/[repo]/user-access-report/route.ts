// REP-1: `GET /{repo}/user-access-report` proxied as is (Content-Disposition, status, X-Error-*).
import type { NextRequest } from "next/server";
import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return forward(req);
}
