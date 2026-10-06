// Requester gate box on the model page (docs/hf-gated/ui.md §A). Pure render: the state comes
// from lib/gateState (auth-check), the texts from lib/gateForm (card metadata).
import type { GateState } from "@/lib/gateState";
import { GATED_REPOS_PATH } from "@/lib/gatedRepos";
import { DEFAULT_GATE_HEADING, submitLabel, type GateConfig, type GateField } from "@/lib/gateForm";
import { countries } from "@/lib/countries";
import { renderMarkdown } from "@/lib/markdown";

type GateBoxState = Exclude<GateState, { kind: "access" }>;
export type GateMode = "auto" | "manual";

interface GateBoxProps {
  repoId: string;
  config: GateConfig;
  state: GateBoxState;
  /** The repo's `gated` mode: it picks the default submit label (Q-11). */
  mode: GateMode;
}

/**
 * A caller with access to a gated repo (auth-check 200): HF shows this block instead of the gate box
 * [OBS-UI 2026-10-06, seen as the owner]. Provisional (Q-11): an accepted requester (A4) is presumed to
 * see the same block; it gives the same auth-check answer as the owner.
 */
export function GatedModelAccess() {
  return (
    <section aria-labelledby="gated-model-heading">
      <h2 id="gated-model-heading">Gated model</h2>
      <p>You have been granted access to this model</p>
    </section>
  );
}

export function GateBox({ repoId, config, state, mode }: GateBoxProps) {
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
      <GateBody repoId={repoId} config={config} state={state} mode={mode} />
    </section>
  );
}

function GateBody({ repoId, config, state, mode }: GateBoxProps) {
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
      return <GateForm repoId={repoId} config={config} mode={mode} />;
    case "reset":
      // A6 [DOC]: after a reset the user is prompted to agree and submit a new request.
      // Provisional (Q-11): whether the page also shows a reset notice (or the resetReason) is unrecorded.
      return <GateForm repoId={repoId} config={config} mode={mode} />;
    case "rejected":
      // A5 [DOC]: the page text from the docs. The rejectionReason is not exposed by the API (REQ-4,
      // Q-19), so it cannot be shown in bridge mode.
      return <p role="status">Your request to access this repo has been rejected by the repo&apos;s authors.</p>;
    case "pending":
      // A3 [OBS-UI 2026-10-06]: HF's own text (not the auth-check message), "your settings" linking to
      // /settings/gated-repos. There is no cancel control on the model page: self-cancel lives there.
      return (
        <p role="status">
          Your request to access this repository has been submitted and is awaiting a review from the repository
          authors. You can check the status of all your access requests in <a href={GATED_REPOS_PATH}>your settings</a>.
        </p>
      );
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
 * A2 [OBS-UI 2026-10-06]: a plain HTML form `POST /{repo}/ask-access?next=/{repo}` (URL-encoded); each
 * field's `name` is its label (gate-form.md: the label is both the visible text and the key of the
 * stored answers). Text order as recorded on `bigcode/starcoder`: the consent line, the fields (YAML
 * order), the button. There is no Cancel button.
 * Not reproduced: HF's hidden `csrf` input (our backends take the persona token; an extra field would
 * change the request body), and the "Expand to review and access" button that collapses long forms
 * (what makes a form "long" is unrecorded).
 */
export function GateForm({ repoId, config, mode }: { repoId: string; config: GateConfig; mode: GateMode }) {
  return (
    <form method="post" action={`/${repoId}/ask-access?next=/${repoId}`}>
      <p>By agreeing you accept to share your contact information (email and username) with the repository authors.</p>
      {config.fields.map((field, i) => (
        <GateFieldInput key={field.label} field={field} id={`gate-field-${i}`} />
      ))}
      <button type="submit">{submitLabel(config, mode)}</button>
    </form>
  );
}

// [OBS-UI 2026-10-06] Every extra field is `required` (checkboxes included); text inputs have the
// placeholder "<Label> (required)"; selects start on an empty "Select an option".
// Values are the browser's native ones (Q-15, matches what HF's form posts): checkbox "on", date
// "YYYY-MM-DD", country ISO alpha-2 code, select option value.
const SELECT_AN_OPTION = <option value="">Select an option</option>;

function GateFieldInput({ field, id }: { field: GateField; id: string }) {
  switch (field.type) {
    case "checkbox":
      return (
        <p>
          <input type="checkbox" id={id} name={field.label} value="on" required />{" "}
          <label htmlFor={id}>{field.label}</label>
        </p>
      );
    case "date_picker":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label> <input type="date" id={id} name={field.label} required />
        </p>
      );
    case "country":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label>{" "}
          <select id={id} name={field.label} defaultValue="" required>
            {SELECT_AN_OPTION}
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
          <select id={id} name={field.label} defaultValue="" required>
            {SELECT_AN_OPTION}
            {field.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </p>
      );
    case "ip_location":
      // No input; the server records the location [OBS-UI 2026-10-06].
      return <p>Your country and region (based on approximate Internet address) will be shared with the model owner.</p>;
    case "text":
      return (
        <p>
          <label htmlFor={id}>{field.label}</label>{" "}
          <input type="text" id={id} name={field.label} placeholder={`${field.label} (required)`} required />
        </p>
      );
    case "unknown":
      // Provisional (Q-15): a type gate-form.md does not document; rendered as a (required) text input.
      return (
        <p>
          <label htmlFor={id}>{field.label}</label>{" "}
          <input
            type="text"
            id={id}
            name={field.label}
            placeholder={`${field.label} (required)`}
            required
            data-unknown-field-type={field.rawType}
          />
        </p>
      );
  }
}
