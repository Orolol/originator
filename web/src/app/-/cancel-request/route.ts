// `POST /-/cancel-request` (form field `repo`): requester self-cancel from the gate box. Forwards to the
// backend's `POST /api/models/{repo}/user-access-request/cancel` with the persona token (api.md, [SPEC]
// "Cancel the current user's access request"; no request body), then redirects back to the repo page.
// Web-app-only route: HF's page control for this (if any) is unrecorded (Q-3), so no HF path is copied.
// Backend errors are relayed verbatim.
import { NextResponse, type NextRequest } from "next/server";
import { backendUnreachable, callBackend, relay } from "@/lib/proxy";

export const dynamic = "force-dynamic";

const REPO_ID = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;

export async function POST(req: NextRequest) {
  const form = await req.formData().catch(() => null);
  const repo = form?.get("repo");
  if (typeof repo !== "string" || !REPO_ID.test(repo) || repo.split("/").some((s) => s === "." || s === "..")) {
    return new Response("Missing or invalid `repo` (expected `namespace/name`).", {
      status: 400,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  let upstream: Response;
  try {
    upstream = await callBackend(req, `/api/models/${repo}/user-access-request/cancel`, { method: "POST", body: "" });
  } catch (err) {
    return backendUnreachable(req, err);
  }
  if (!upstream.ok) return relay(upstream, req);
  return NextResponse.redirect(new URL(`/${repo}`, req.nextUrl.origin), 303);
}
