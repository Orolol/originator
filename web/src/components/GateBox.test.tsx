import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { GateBox, GatedModelAccess } from "./GateBox";
import { gateConfigFromCardData } from "@/lib/gateForm";
import { GEMMA_CARD, LLAMA_CARD, STARCODER_CARD } from "@/test/fixtures";

const REPO = "meta-llama/Llama-3.2-1B";
const DEFAULT_HEADING = "You need to agree to share your contact information to access this model";
const DEFAULT_SUBLINE =
  "This repository is publicly accessible, but you have to accept the conditions to access its files and content.";
const CONSENT =
  "By agreeing you accept to share your contact information (email and username) with the repository authors.";

type Props = Parameters<typeof GateBox>[0];

function renderGate(card: object, state: Props["state"], mode: Props["mode"] = "manual") {
  return render(<GateBox repoId={REPO} config={gateConfigFromCardData(card)} state={state} mode={mode} />);
}

/** Element whose whole text (across child elements) equals `text`. */
const fullText = (tag: string, text: string) => (_: string, el: Element | null) =>
  el?.tagName === tag && el.textContent === text;

describe("A1 anonymous (ui.md §A1 [OBS])", () => {
  it("shows heading, sub-line, prompt and the log-in line, and no form", () => {
    const { container } = renderGate(STARCODER_CARD, { kind: "anonymous", message: "" });
    expect(screen.getByRole("heading", { name: DEFAULT_HEADING })).toBeTruthy();
    expect(screen.getByText(fullText("P", DEFAULT_SUBLINE))).toBeTruthy();
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

describe("A2 logged in, no request: gate form from extra_gated_fields [OBS-UI 2026-10-06]", () => {
  it("is a plain POST to ask-access?next=/{repo}: consent line, then every field in YAML order, all required", () => {
    const { container } = renderGate(LLAMA_CARD, { kind: "no-request", message: "" });
    const form = container.querySelector("form")!;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBe(`/${REPO}/ask-access?next=/${REPO}`);

    const consentLabel = Object.keys(LLAMA_CARD.extra_gated_fields)[7];
    const named = [...form.querySelectorAll("[name]")].map((el) => [
      el.getAttribute("name"),
      el.tagName,
      el.getAttribute("type"),
      el.getAttribute("placeholder"),
      el.hasAttribute("required"),
    ]);
    expect(named).toEqual([
      ["First Name", "INPUT", "text", "First Name (required)", true],
      ["Last Name", "INPUT", "text", "Last Name (required)", true],
      ["Date of birth", "INPUT", "date", null, true],
      ["Country", "SELECT", null, null, true],
      ["Affiliation", "INPUT", "text", "Affiliation (required)", true],
      ["Job title", "SELECT", null, null, true],
      // `geo: ip_location` renders no input, only the line checked below
      [consentLabel, "INPUT", "checkbox", null, true],
    ]);
    expect(screen.getByRole("checkbox", { name: consentLabel }).getAttribute("value")).toBe("on");
    expect(
      screen.getByText(
        "Your country and region (based on approximate Internet address) will be shared with the model owner.",
      ),
    ).toBeTruthy();
    // Text order recorded on bigcode/starcoder: the consent line comes before the fields.
    const consent = screen.getByText(CONSENT);
    expect(consent.compareDocumentPosition(screen.getByRole("textbox", { name: "First Name" }))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );

    const country = screen.getByRole("combobox", { name: "Country" }) as HTMLSelectElement;
    expect(country.options).toHaveLength(250); // "Select an option" + 249 ISO 3166-1 alpha-2 codes
    expect(within(country).getByRole("option", { name: "France" }).getAttribute("value")).toBe("FR");
    const job = screen.getByRole("combobox", { name: "Job title" }) as HTMLSelectElement;
    expect([...job.options].map((o) => [o.textContent, o.value])).toEqual([
      ["Select an option", ""],
      ...LLAMA_CARD.extra_gated_fields["Job title"].options.map((o) => [o, o]),
    ]);
    expect(country.value).toBe("");
    expect(job.value).toBe("");
  });

  it("select options may be {label, value} objects", () => {
    renderGate(
      { extra_gated_fields: { Usage: { type: "select", options: [{ label: "Research use", value: "research" }, "Other"] } } },
      { kind: "no-request", message: "" },
    );
    const opts = within(screen.getByRole("combobox", { name: "Usage" })).getAllByRole("option") as HTMLOptionElement[];
    expect(opts.map((o) => [o.textContent, o.value])).toEqual([
      ["Select an option", ""],
      ["Research use", "research"],
      ["Other", "Other"],
    ]);
  });

  it.each([
    ["auto mode, default label", STARCODER_CARD, "auto", "Agree and access repository"],
    ["manual mode, default label", STARCODER_CARD, "manual", "Agree and send request to access repo"],
    ["extra_gated_button_content wins", LLAMA_CARD, "manual", "Submit"],
    ["extra_gated_button_content wins in auto mode too", GEMMA_CARD, "auto", "Acknowledge license"],
  ] as const)("%s, and no Cancel button", (_name, card, mode, label) => {
    renderGate(card, { kind: "no-request", message: "" }, mode);
    expect(screen.getByText(CONSENT)).toBeTruthy();
    expect(screen.getAllByRole("button").map((b) => [b.textContent, b.getAttribute("type")])).toEqual([[label, "submit"]]);
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
    expect(container.querySelector(`form[action="/${REPO}/ask-access?next=/${REPO}"]`)).not.toBeNull();
    expect(screen.getByText(CONSENT)).toBeTruthy();
  });
});

describe("A3 pending, access and unmapped states", () => {
  it("pending shows HF's text linking to /settings/gated-repos, no form and no cancel control [OBS-UI 2026-10-06]", () => {
    const msg = `Your request to access model ${REPO} is awaiting a review from the repo authors.`;
    const { container } = renderGate(STARCODER_CARD, { kind: "pending", message: msg });
    expect(screen.getByRole("status").textContent).toBe(
      "Your request to access this repository has been submitted and is awaiting a review from the repository " +
        "authors. You can check the status of all your access requests in your settings.",
    );
    expect(screen.getByRole("link", { name: "your settings" }).getAttribute("href")).toBe("/settings/gated-repos");
    expect(container.textContent).not.toContain(msg); // not the API message
    expect(container.querySelector("form")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("access (owner, presumably accepted) shows the Gated model block [OBS-UI 2026-10-06]", () => {
    const { container } = render(<GatedModelAccess />);
    expect(screen.getByRole("heading", { name: "Gated model" })).toBeTruthy();
    expect(container.textContent).toContain("You have been granted access to this model");
  });

  it("unmapped shows the message verbatim and flags it", () => {
    const msg = "Something the KB has not recorded";
    renderGate(STARCODER_CARD, { kind: "unmapped", status: 403, code: "GatedRepo", message: msg });
    const status = screen.getByRole("status");
    expect(status.textContent).toContain(msg);
    expect(status.textContent).toContain("unmapped gate state: auth-check HTTP 403 GatedRepo");
  });
});
