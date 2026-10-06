import { describe, expect, it } from "vitest";
import { deriveGateState, gatedRepoRequestStatus } from "./gateState";

const ID = "Orosius/deltanet-mla-latent";
// Messages as observed (api.md §3.1, observations/2026-10-05-*.md).
const ANON = `Access to model ${ID} is restricted. You must have access to it and be authenticated to access it. Please log in.`;
const NO_REQUEST = `Access to model ${ID} is restricted and you are not in the authorized list. Visit https://huggingface.co/${ID} to ask for access.`;
const PENDING = `Your request to access model ${ID} is awaiting a review from the repo authors.`;
const REJECTED = `Your request to access model ${ID} has been rejected by the repo's authors.`;
const RESET = `Your request to access model ${ID} has been reset by the repo's authors. Visit https://huggingface.co/${ID} to submit a new request.`;

describe("deriveGateState (docs/system.md: requester gate state comes from auth-check)", () => {
  it.each([
    ["200 → access (owner bypass ACC-1 or accepted)", { status: 200, code: null, message: "" }, "access"],
    ["401 GatedRepo → anonymous (A1)", { status: 401, code: "GatedRepo", message: ANON }, "anonymous"],
    ["403 GatedRepo not in list → no request (A2)", { status: 403, code: "GatedRepo", message: NO_REQUEST }, "no-request"],
    ["403 GatedRepo awaiting review → pending (A3)", { status: 403, code: "GatedRepo", message: PENDING }, "pending"],
    ["403 GatedRepo rejected → rejected (A5)", { status: 403, code: "GatedRepo", message: REJECTED }, "rejected"],
    ["403 GatedRepo reset → reset (A6)", { status: 403, code: "GatedRepo", message: RESET }, "reset"],
  ])("%s", (_name, input, kind) => {
    expect(deriveGateState(input).kind).toBe(kind);
  });

  it("keeps the backend's pending message for display", () => {
    expect(deriveGateState({ status: 403, code: "GatedRepo", message: PENDING })).toEqual({
      kind: "pending",
      message: PENDING,
    });
  });

  it.each([
    ["unknown GatedRepo message", { status: 403, code: "GatedRepo", message: "Access to this repo is suspended." }],
    ["known message without GatedRepo code", { status: 403, code: null, message: PENDING }],
    ["unknown repo, anonymous", { status: 401, code: null, message: "Invalid username or password." }],
    ["bridge refusal", { status: 403, code: "BridgeRepoNotAllowed", message: "Repo not allowed" }],
  ])("%s → unmapped, verbatim", (_name, input) => {
    expect(deriveGateState(input)).toEqual({ kind: "unmapped", ...input });
  });
});

describe("gatedRepoRequestStatus (/settings/gated-repos rows)", () => {
  it.each([
    [{ kind: "pending", message: PENDING }, "pending"],
    [{ kind: "rejected", message: REJECTED }, "rejected"],
    [{ kind: "reset", message: RESET }, "reset"],
    [{ kind: "no-request", message: NO_REQUEST }, null],
    [{ kind: "anonymous", message: ANON }, null],
    // 200: accepted and the owner bypass (ACC-1) look the same, so no row.
    [{ kind: "access" }, null],
    [{ kind: "unmapped", status: 502, code: null, message: "down" }, null],
  ] as const)("%j → %s", (state, status) => {
    expect(gatedRepoRequestStatus(state)).toBe(status);
  });
});
