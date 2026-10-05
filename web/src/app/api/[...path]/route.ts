// `/api/*` on the web origin → the chosen backend's `/api/*` with the persona's token (docs/system.md).
// Path and query verbatim; status, body and the allow-listed headers passed back.
import type { NextRequest } from "next/server";
import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return forward(req);
}

export function HEAD(req: NextRequest) {
  return forward(req);
}

export function POST(req: NextRequest) {
  return forward(req);
}

export function PUT(req: NextRequest) {
  return forward(req);
}

export function DELETE(req: NextRequest) {
  return forward(req);
}
