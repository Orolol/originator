// Requester gate box on the model page (docs/hf-gated/ui.md §A). Pure render: the state comes
// from lib/gateState (auth-check), the texts from lib/gateForm (card metadata).
import type { GateState } from "@/lib/gateState";
import { DEFAULT_GATE_HEADING, DEFAULT_SUBMIT_LABEL, type GateConfig, type GateField } from "@/lib/gateForm";
import { countries } from "@/lib/countries";
import { renderMarkdown } from "@/lib/markdown";

type GateBoxState = Exclude<GateState, { kind: "access" }>;

export function GateBox({ repoId, config, state }: { repoId: string; config: GateConfig; state: GateBoxState }) {
  return (
    <section aria-labelledby="gate-heading" data-gate-state={state.kind}>
      <h2 id="gate-heading">{config.heading ?? DEFAULT_GATE_HEADING}</h2>
      {config.description ? (
        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(config.description) }} />
      ) : (
        <p>
          This repository is publicly accessible, but{" "}
          <strong>you have to accept the conditions to access its files and content</strong>.
        </p>
      )}
      {config.prompt && <div dangerouslySetInnerHTML={{ __html: renderMarkdown(config.prompt) }} />}
      <GateBody repoId={repoId} config={config} state={state} />
    </section>
  );
}

function GateBody({ repoId, config, state }: { repoId: string; config: GateConfig; state: GateBoxState }) {
  const back = encodeURIComponent(`/${repoId}`);
  switch (state.kind) {
    case "anonymous":
      // A1 [OBS], REQ-1: no form fields for anonymous visitors.
      // Provisional (no Q-id yet): HF links to its own log-in / sign-up pages; the web app has no
      // login, so both links switch to the requester persona.
      return (
        <p>
          <a href={`/-/persona?as=requester&next=${back}`}>Log in</a> or{" "}
          <a href={`/-/persona?as=requester&next=${back}`}>Sign Up</a> to review the conditions and access this
          model content.
        </p>
      );
    case "no-request":
      return <GateForm repoId={repoId} config={config} />;
    case "reset":
      // A6 [DOC]: after a reset the user is prompted to agree and submit a new request.
      // Provisional (Q-11): whether the page also shows a reset notice (or the resetReason) is unrecorded.
      return <GateForm repoId={repoId} config={config} />;
    case "rejected":
      // A5 [DOC]: the page text from the docs. The rejectionReason is not exposed by the API (REQ-4,
      // Q-19), so it cannot be shown in bridge mode.
      return <p role="status">Your request to access this repo has been rejected by the repo&apos;s authors.</p>;
    case "pending":
      // Provisional (Q-11): the page wording for A3 is unrecorded; we show the backend's auth-check
      // message verbatim ("Your request to access model {id} is awaiting a review from the repo authors.").
      return <p role="status">{state.message}</p>;
    case "unmapped":
      // docs/system.md: unknown auth-check answers are shown verbatim and flagged, never mapped to a
      // guessed screen.
      return (
        <div role="status">
          <p>{state.message}</p>
          <p>
            <small>
              [unmapped gate state: auth-check HTTP {state.status}
              {state.code ? ` ${state.code}` : ""}]
            </small>
          </p>
        </div>
      );
  }
}

/**
 * A2: plain HTML form POST to `/{repo}/ask-access`; each field's `name` is its label (gate-form.md:
 * the label is both the visible text and the key of the stored answers).
 */
export function GateForm({ repoId, config }: { repoId: string; config: GateConfig }) {
  return (
    <form method="post" action={`/${repoId}/ask-access`}>
      {config.fields.map((field, i) => (
        <GateFieldInput key={field.label} field={field} id={`gate-field-${i}`} />
      ))}
      <p>By agreeing you accept to share your contact information (email and username) with the repository authors.</p>
      {/* Provisional (Q-11): whether the default label differs in auto mode is unrecorded; same label. */}
      <button type="submit">{config.buttonContent ?? DEFAULT_SUBMIT_LABEL}</button>{" "}
      {/* Provisional (Q-11): what Cancel does is unrecorded; it does nothing here. */}
      <button type="button">Cancel</button>
    </form>
  );
}

// Provisional (Q-16): whether fields are required / checkboxes must be checked is unknown, so no
// client-side validation is added; the backend decides.
// Provisional (Q-15): submitted values are the browser's native ones (checkbox "on", date
// "YYYY-MM-DD", country alpha-2 code, select option value).
function GateFieldInput({ field, id }: { field: GateField; id: string }) {
  switch (field.type) {
    case "checkbox":
      return (
        <p>
          <input type="checkbox" id={id} name={field.label} /> <label htmlFor={id}>{field.label}</label>
        </p>
      );
    case "date_picker":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label> <input type="date" id={id} name={field.label} />
        </p>
      );
    case "country":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label>{" "}
          <select id={id} name={field.label} defaultValue="">
            {/* Provisional (Q-16): empty first option, so nothing is pre-selected. */}
            <option value=""></option>
            {countries().map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </p>
      );
    case "select":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label>{" "}
          <select id={id} name={field.label} defaultValue="">
            {/* Provisional (Q-16): empty first option, so nothing is pre-selected. */}
            <option value=""></option>
            {field.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </p>
      );
    case "ip_location":
      // Provisional (Q-15): undocumented type; no input (the server presumably records the IP location).
      return null;
    case "text":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label> <input type="text" id={id} name={field.label} />
        </p>
      );
    case "unknown":
      // Provisional (Q-15): a type gate-form.md does not document; rendered as a text input.
      return (
        <p>
          <label htmlFor={id}>{field.label}</label>{" "}
          <input type="text" id={id} name={field.label} data-unknown-field-type={field.rawType} />
        </p>
      );
  }
}
