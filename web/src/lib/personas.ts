// Personas (docs/system.md "Personas"). The web app only ever holds these fake tokens; the
// backend (bridge or clone) maps them to real identities. Shared by server and client code.

export const PERSONA_COOKIE = "persona";

export const PERSONAS = {
  anonymous: { token: null },
  owner: { token: "persona-owner" },
  requester: { token: "persona-requester" },
} as const;

export type PersonaId = keyof typeof PERSONAS;

export const PERSONA_IDS = Object.keys(PERSONAS) as PersonaId[];

export function isPersonaId(value: unknown): value is PersonaId {
  return typeof value === "string" && Object.hasOwn(PERSONAS, value);
}

/** Unknown or missing cookie values fall back to the anonymous persona. */
export function parsePersona(value: string | undefined | null): PersonaId {
  return isPersonaId(value) ? value : "anonymous";
}

/** `Authorization` header for the persona; anonymous sends none. */
export function authHeaders(persona: PersonaId): Record<string, string> {
  const token = PERSONAS[persona].token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
