// `GET|HEAD /{repo}/resolve/{rev}/{path}` proxied as is: the gate (ACC-3, ACC-5, ACC-6) is the
// backend's decision; redirects (CDN) are passed to the browser untouched.
import type { NextRequest } from "next/server";
import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return forward(req);
}

export function HEAD(req: NextRequest) {
  return forward(req);
}
