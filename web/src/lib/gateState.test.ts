import { describe, expect, it } from "vitest";
import { deriveGateState } from "./gateState";

const ID = "Orosius/deltanet-mla-latent";
// Messages as observed (api.md §3.1, observations/2026-10-05-*.md).
const ANON = `Access to model ${ID} is restricted. You must have access to it and be authenticated to access it. Please log in.`;
const NO_REQUEST = `Access to model ${ID} is restricted and you are not in the authorized list. Visit https://huggingface.co/${ID} to ask for access.`;
const PENDING = `Your request to access model ${ID} is awaiting a review from the repo authors.`;

describe("deriveGateState (docs/system.md: requester gate state comes from auth-check)", () => {
  it.each([
    ["200 → access (owner bypass ACC-1 or accepted)", { status: 200, code: null, message: "" }, "access"],
    ["401 GatedRepo → anonymous (A1)", { status: 401, code: "GatedRepo", message: ANON }, "anonymous"],
    ["403 GatedRepo not in list → no request (A2)", { status: 403, code: "GatedRepo", message: NO_REQUEST }, "no-request"],
    ["403 GatedRepo awaiting review → pending (A3)", { status: 403, code: "GatedRepo", message: PENDING }, "pending"],
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
    // Rejected (A5) is not recorded through the API [Q-8]: must stay unmapped, never guessed.
    ["unknown GatedRepo message", { status: 403, code: "GatedRepo", message: "Your request to access this repo has been rejected by the repo's authors." }],
    ["known message without GatedRepo code", { status: 403, code: null, message: PENDING }],
    ["unknown repo, anonymous", { status: 401, code: null, message: "Invalid username or password." }],
    ["bridge refusal", { status: 403, code: "BridgeRepoNotAllowed", message: "Repo not allowed" }],
  ])("%s → unmapped, verbatim", (_name, input) => {
    expect(deriveGateState(input)).toEqual({ kind: "unmapped", ...input });
  });
});
