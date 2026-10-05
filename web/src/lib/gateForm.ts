// `extra_gated_*` card metadata → gate box configuration (docs/hf-gated/gate-form.md).

export type GateFieldType = "text" | "checkbox" | "date_picker" | "country" | "select" | "ip_location";

export interface SelectOption {
  label: string;
  value: string;
}

export type GateField =
  | { label: string; type: Exclude<GateFieldType, "select"> }
  | { label: string; type: "select"; options: SelectOption[] }
  /** A type gate-form.md does not document. */
  | { label: string; type: "unknown"; rawType: string };

export interface GateConfig {
  /** `extra_gated_heading`, replaces the default heading. */
  heading: string | null;
  /** `extra_gated_description` (markdown), replaces the default sub-line. */
  description: string | null;
  /** `extra_gated_prompt` (markdown). */
  prompt: string | null;
  /** `extra_gated_button_content`, replaces the submit button label. */
  buttonContent: string | null;
  /** `extra_gated_fields`, in YAML (object key) order [Q-11]. */
  fields: GateField[];
}

export const DEFAULT_GATE_HEADING = "You need to agree to share your contact information to access this model";
export const DEFAULT_SUBMIT_LABEL = "Agree and send request to access repo";

const KNOWN_TYPES: readonly string[] = ["text", "checkbox", "date_picker", "country", "select", "ip_location"];

function str(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function normalizeOptions(raw: unknown): SelectOption[] {
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((opt): SelectOption[] => {
    // `options: [string | {label, value}]` [DOC] [JS]
    if (typeof opt === "string") return [{ label: opt, value: opt }];
    if (opt && typeof opt === "object") {
      const { label, value } = opt as { label?: unknown; value?: unknown };
      if (typeof label === "string" || typeof value === "string") {
        const v = String(value ?? label);
        return [{ label: String(label ?? v), value: v }];
      }
    }
    return [];
  });
}

/** A field spec is either a bare type string or `{type: …}` (gate-form.md §2). */
export function normalizeGateFields(raw: unknown): GateField[] {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];
  return Object.entries(raw as Record<string, unknown>).map(([label, spec]): GateField => {
    const type =
      typeof spec === "string"
        ? spec
        : spec && typeof spec === "object"
          ? String((spec as { type?: unknown }).type ?? "")
          : "";
    if (type === "select") {
      return { label, type: "select", options: normalizeOptions((spec as { options?: unknown }).options) };
    }
    if (KNOWN_TYPES.includes(type)) return { label, type: type as Exclude<GateFieldType, "select"> };
    return { label, type: "unknown", rawType: type };
  });
}

export function gateConfigFromCardData(cardData: unknown): GateConfig {
  const card = (cardData && typeof cardData === "object" ? cardData : {}) as Record<string, unknown>;
  return {
    heading: str(card.extra_gated_heading),
    description: str(card.extra_gated_description),
    prompt: str(card.extra_gated_prompt),
    buttonContent: str(card.extra_gated_button_content),
    fields: normalizeGateFields(card.extra_gated_fields),
  };
}
