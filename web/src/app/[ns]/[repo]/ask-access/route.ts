// Requester submits the gate form (ui.md §A2, REQ-2): the browser posts a plain HTML form here, at
// `/{repo}/ask-access?next=/{repo}` like HF's form [OBS-UI 2026-10-06]; we forward the answers to the
// backend's `POST /{repo}/ask-access` as a JSON object `{<field label>: <value>}` (api.md §1: JSON or
// form-encoded both work [OBS]; JSON matches the spec).
// Backend 303 → browser 303 to the repo page on the web origin; anything else is relayed verbatim.
// Provisional (Q-11): what HF does with `next` is unrecorded. It is accepted and not forwarded (the
// recorded walkthroughs posted without it); the redirect follows the backend's 303, which is the repo
// page, i.e. the `next` our form sends.
import type { NextRequest } from "next/server";
import { backendUnreachable, backendUrlFromRequest, callBackend, relay } from "@/lib/proxy";

export const dynamic = "force-dynamic";

async function submittedFields(req: NextRequest): Promise<Record<string, unknown>> {
  const contentType = req.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const body: unknown = await req.json().catch(() => ({}));
    return body && typeof body === "object" && !Array.isArray(body) ? (body as Record<string, unknown>) : {};
  }
  if (contentType.includes("application/x-www-form-urlencoded") || contentType.includes("multipart/form-data")) {
    const form = await req.formData();
    const fields: Record<string, unknown> = {};
    form.forEach((value, key) => {
      fields[key] = typeof value === "string" ? value : value.name;
    });
    return fields;
  }
  return {};
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ ns: string; repo: string }> }) {
  const { ns, repo } = await ctx.params;
  const fields = await submittedFields(req);
  let upstream: Response;
  try {
    upstream = await callBackend(req, req.nextUrl.pathname, {
      method: "POST",
      body: JSON.stringify(fields),
      contentType: "application/json",
      search: "",
    });
  } catch (err) {
    return backendUnreachable(req, err);
  }
  if (upstream.status === 303) {
    // HF answers `303 Location: https://huggingface.co/{repo}` (the bridge rewrites the host). Keep
    // the target path, on the web origin.
    const location = upstream.headers.get("location");
    const target = location ? new URL(location, backendUrlFromRequest(req)) : null;
    const path = target ? `${target.pathname}${target.search}` : `/${ns}/${repo}`;
    return new Response(null, { status: 303, headers: { location: new URL(path, req.nextUrl.origin).toString() } });
  }
  return relay(upstream, req);
}
