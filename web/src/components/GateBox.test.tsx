import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { GateBox } from "./GateBox";
import { gateConfigFromCardData } from "@/lib/gateForm";
import { GEMMA_CARD, LLAMA_CARD, STARCODER_CARD } from "@/test/fixtures";

const REPO = "meta-llama/Llama-3.2-1B";
const DEFAULT_HEADING = "You need to agree to share your contact information to access this model";
const DEFAULT_SUBLINE =
  "This repository is publicly accessible, but you have to accept the conditions to access its files and content.";
const CONSENT =
  "By agreeing you accept to share your contact information (email and username) with the repository authors.";

function renderGate(card: object, state: Parameters<typeof GateBox>[0]["state"]) {
  return render(<GateBox repoId={REPO} config={gateConfigFromCardData(card)} state={state} />);
}

describe("A1 anonymous (ui.md §A1 [OBS])", () => {
  it("shows heading, sub-line, prompt and the log-in line, and no form", () => {
    const { container } = renderGate(STARCODER_CARD, { kind: "anonymous", message: "" });
    expect(screen.getByRole("heading", { name: DEFAULT_HEADING })).toBeTruthy();
    expect(screen.getByText((_, el) => el?.tagName === "P" && el.textContent === DEFAULT_SUBLINE)).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Model License Agreement" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Log in" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign Up" })).toBeTruthy();
    expect(container.textContent).toContain("to review the conditions and access this model content.");
    expect(container.querySelector("form")).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("uses extra_gated_heading; extra_gated_description replaces the sub-line", () => {
    renderGate(GEMMA_CARD, { kind: "anonymous", message: "" });
    expect(screen.getByRole("heading", { name: "Access Gemma on Hugging Face" })).toBeTruthy();
    renderGate(LLAMA_CARD, { kind: "anonymous", message: "" });
    expect(screen.getByRole("link", { name: "Meta Privacy Policy" })).toBeTruthy();
    expect(screen.getAllByText(/This repository is publicly accessible/)).toHaveLength(1); // Gemma only
  });
});

describe("A2 logged in, no request: gate form from extra_gated_fields (gate-form.md §2)", () => {
  it("renders every field type in YAML order, named by label, posting to ask-access", () => {
    const { container } = renderGate(LLAMA_CARD, { kind: "no-request", message: "" });
    const form = container.querySelector("form")!;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBe(`/${REPO}/ask-access`);

    const named = [...form.querySelectorAll("[name]")].map((el) => [el.getAttribute("name"), el.tagName, el.getAttribute("type")]);
    const consentLabel = Object.keys(LLAMA_CARD.extra_gated_fields)[7];
    expect(named).toEqual([
      ["First Name", "INPUT", "text"],
      ["Last Name", "INPUT", "text"],
      ["Date of birth", "INPUT", "date"],
      ["Country", "SELECT", null],
      ["Affiliation", "INPUT", "text"],
      ["Job title", "SELECT", null],
      // `geo: ip_location` renders no input (Q-15)
      [consentLabel, "INPUT", "checkbox"],
    ]);

    expect(screen.getByRole("textbox", { name: "First Name" })).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: consentLabel })).toBeTruthy();
    const country = screen.getByRole("combobox", { name: "Country" }) as HTMLSelectElement;
    expect(country.options).toHaveLength(250); // empty + 249 ISO 3166-1 alpha-2 codes
    expect(within(country).getByRole("option", { name: "France" }).getAttribute("value")).toBe("FR");
    const job = screen.getByRole("combobox", { name: "Job title" }) as HTMLSelectElement;
    expect([...job.options].map((o) => o.value)).toEqual(["", ...LLAMA_CARD.extra_gated_fields["Job title"].options]);
  });

  it("select options may be {label, value} objects", () => {
    renderGate(
      { extra_gated_fields: { Usage: { type: "select", options: [{ label: "Research use", value: "research" }, "Other"] } } },
      { kind: "no-request", message: "" },
    );
    const opts = within(screen.getByRole("combobox", { name: "Usage" })).getAllByRole("option") as HTMLOptionElement[];
    expect(opts.map((o) => [o.textContent, o.value])).toEqual([
      ["", ""],
      ["Research use", "research"],
      ["Other", "Other"],
    ]);
  });

  it.each([
    ["default button label", STARCODER_CARD, "Agree and send request to access repo"],
    ["extra_gated_button_content", LLAMA_CARD, "Submit"],
  ])("consent line, %s and Cancel", (_name, card, label) => {
    renderGate(card, { kind: "no-request", message: "" });
    expect(screen.getByText(CONSENT)).toBeTruthy();
    expect(screen.getByRole("button", { name: label }).getAttribute("type")).toBe("submit");
    expect(screen.getByRole("button", { name: "Cancel" }).getAttribute("type")).toBe("button");
  });
});

describe("A5 rejected and A6 reset (OBS 2026-10-05)", () => {
  it("rejected shows the documented page text and no form (the reason is not exposed by the API)", () => {
    const msg = `Your request to access model ${REPO} has been rejected by the repo's authors.`;
    const { container } = renderGate(STARCODER_CARD, { kind: "rejected", message: msg });
    expect(screen.getByRole("status").textContent).toBe(
      "Your request to access this repo has been rejected by the repo's authors.",
    );
    expect(container.querySelector("form")).toBeNull();
  });

  it("reset shows the consent form again", () => {
    const msg = `Your request to access model ${REPO} has been reset by the repo's authors.`;
    const { container } = renderGate(STARCODER_CARD, { kind: "reset", message: msg });
    expect(container.querySelector(`form[action="/${REPO}/ask-access"]`)).not.toBeNull();
    expect(screen.getByText(CONSENT)).toBeTruthy();
  });
});

describe("A3 pending and unmapped states", () => {
  it("pending shows the backend message, no form", () => {
    const msg = `Your request to access model ${REPO} is awaiting a review from the repo authors.`;
    const { container } = renderGate(STARCODER_CARD, { kind: "pending", message: msg });
    expect(screen.getByRole("status").textContent).toBe(msg);
    expect(container.querySelector("form")).toBeNull();
  });

  it("unmapped shows the message verbatim and flags it", () => {
    const msg = "Something the KB has not recorded";
    renderGate(STARCODER_CARD, { kind: "unmapped", status: 403, code: "GatedRepo", message: msg });
    const status = screen.getByRole("status");
    expect(status.textContent).toContain(msg);
    expect(status.textContent).toContain("unmapped gate state: auth-check HTTP 403 GatedRepo");
  });
});
