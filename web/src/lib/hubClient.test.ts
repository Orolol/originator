import { describe, expect, it } from "vitest";
import { accessRequestsUrl, nextPageUrl } from "./hubClient";

const REPO = "OwnerOfTheGatedModel/tiny-gated-model";
const LIST = `/api/models/${REPO}/user-access-request/pending`;

describe("accessRequestsUrl: the modal's list requests [OBS-UI 2026-10-06]", () => {
  it.each([
    ["", `${LIST}?limit=100`],
    ["testing", `${LIST}?limit=100&q=testing`],
    ["a b&c", `${LIST}?limit=100&q=a+b%26c`],
  ])("q=%j → %s", (q, url) => {
    expect(accessRequestsUrl(REPO, "pending", q)).toBe(url);
  });
});

describe("nextPageUrl: Link rel=next (REV-10) → a path fetched through the web /api proxy", () => {
  it.each([
    ["web origin (proxy-rewritten)", `<http://localhost:3000${LIST}?limit=100&after=x>; rel="next"`, `${LIST}?limit=100&after=x`],
    ["backend host left as is", `<http://127.0.0.1:8200${LIST}?after=x>; rel="next"`, `${LIST}?after=x`],
    ["several links", `<http://h/a>; rel="prev", <http://h${LIST}?after=y>; rel="next"`, `${LIST}?after=y`],
    ["no next link", `<http://h${LIST}?after=y>; rel="prev"`, null],
    ["outside /api/", `<http://evil.example/steal>; rel="next"`, null],
    ["no header", null, null],
  ])("%s", (_name, link, expected) => {
    expect(nextPageUrl(link)).toBe(expected);
  });
});
