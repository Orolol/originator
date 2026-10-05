// @vitest-environment node
// Web routes → backend (docs/system.md "Web app conventions"): persona token, path/query verbatim,
// allow-listed headers, ask-access form → JSON and 303 → repo page on the web origin.
import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/lib/config";
import { POST as askAccess } from "@/app/[ns]/[repo]/ask-access/route";
import { GET as apiGet } from "@/app/api/[...path]/route";
import { GET as switchPersona } from "@/app/-/persona/route";

const WEB = "http://localhost:3000";
const REPO = "Orosius/deltanet-mla-latent";

function stubBackend(response: () => Response) {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () => response());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function sentHeaders(init: RequestInit | undefined): Record<string, string> {
  return (init?.headers ?? {}) as Record<string, string>;
}

describe("POST /{repo}/ask-access", () => {
  const params = Promise.resolve({ ns: "Orosius", repo: "deltanet-mla-latent" });

  function formPost(fields: Record<string, string>) {
    return new NextRequest(`${WEB}/${REPO}/ask-access`, {
      method: "POST",
      body: new URLSearchParams(fields),
      headers: { cookie: "persona=requester", "content-type": "application/x-www-form-urlencoded" },
    });
  }

  it("forwards the form as a JSON object {label: value} and turns the backend 303 into a web 303", async () => {
    const fetchMock = stubBackend(
      () => new Response(null, { status: 303, headers: { location: `${BACKEND_URL}/${REPO}` } }),
    );
    const res = await askAccess(formPost({ "First Name": "Ada", "Job title": "Other" }), { params });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BACKEND_URL}/${REPO}/ask-access`);
    expect(init?.method).toBe("POST");
    expect(sentHeaders(init)).toEqual({ Authorization: "Bearer persona-requester", "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual({ "First Name": "Ada", "Job title": "Other" });
    expect(init?.redirect).toBe("manual");
    expect(res.status).toBe(303);
    expect(res.headers.get("location")).toBe(`${WEB}/${REPO}`);
  });

  it("relays a backend error verbatim (status, X-Error-*, body)", async () => {
    stubBackend(
      () =>
        new Response("Nope", {
          status: 403,
          headers: { "x-error-code": "GatedRepo", "x-error-message": "Nope", "set-cookie": "a=b" },
        }),
    );
    const res = await askAccess(formPost({}), { params });
    expect(res.status).toBe(403);
    expect(res.headers.get("x-error-code")).toBe("GatedRepo");
    expect(res.headers.get("x-error-message")).toBe("Nope");
    expect(res.headers.get("set-cookie")).toBeNull();
    expect(await res.text()).toBe("Nope");
  });
});

describe("/api/* proxy", () => {
  it.each([
    ["owner", { Authorization: "Bearer persona-owner" }],
    ["requester", { Authorization: "Bearer persona-requester" }],
    ["anonymous", {}],
    ["bogus", {}], // unknown cookie → anonymous
  ])("persona %s → Authorization %j, path and query verbatim", async (persona, auth) => {
    const fetchMock = stubBackend(() => Response.json([]));
    const path = `/api/models/${REPO}/user-access-request/pending?limit=10&expand[]=gated`;
    await apiGet(new NextRequest(`${WEB}${path}`, { headers: { cookie: `persona=${persona}` } }));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BACKEND_URL}${path}`);
    expect(sentHeaders(init)).toEqual(auth);
  });

  it("passes back status, body and the listed headers only; backend URLs in Link point to the web origin", async () => {
    stubBackend(
      () =>
        new Response('{"error":"Invalid username or password."}', {
          status: 401,
          headers: {
            "content-type": "application/json",
            "x-error-message": "Invalid username or password.",
            "www-authenticate": 'Bearer realm="Authentication required", charset="UTF-8"',
            link: `<${BACKEND_URL}/api/models/${REPO}/user-access-request/pending?cursor=x>; rel="next"`,
            "set-cookie": "token=secret",
            "x-powered-by": "upstream",
          },
        }),
    );
    const res = await apiGet(new NextRequest(`${WEB}/api/models/${REPO}/user-access-request/pending`));
    expect(res.status).toBe(401);
    expect(await res.text()).toBe('{"error":"Invalid username or password."}');
    expect([...res.headers.keys()].sort()).toEqual(["content-type", "link", "www-authenticate", "x-error-message"]);
    expect(res.headers.get("link")).toBe(`<${WEB}/api/models/${REPO}/user-access-request/pending?cursor=x>; rel="next"`);
  });
});

describe("GET /-/persona", () => {
  it("sets the cookie and redirects to a same-origin path only", async () => {
    const ok = switchPersona(new NextRequest(`${WEB}/-/persona?as=owner&next=/${REPO}/settings`));
    expect(ok.status).toBe(303);
    expect(ok.headers.get("location")).toBe(`${WEB}/${REPO}/settings`);
    expect(ok.headers.get("set-cookie")).toContain("persona=owner");
    const external = switchPersona(new NextRequest(`${WEB}/-/persona?as=owner&next=//evil.example`));
    expect(external.headers.get("location")).toBe(`${WEB}/`);
    expect(switchPersona(new NextRequest(`${WEB}/-/persona?as=admin`)).status).toBe(400);
  });
});
