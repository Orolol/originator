"use client";
// Links to `/-/persona?as=…&next=<current path>` (docs/system.md "Web app conventions").
import { usePathname } from "next/navigation";
import { PERSONA_IDS, type PersonaId } from "@/lib/personas";

export function PersonaSwitcher({ current }: { current: PersonaId }) {
  const pathname = usePathname() ?? "/";
  return (
    <nav aria-label="Switch persona">
      Switch persona:{" "}
      {PERSONA_IDS.map((p, i) => (
        <span key={p}>
          {i > 0 && " | "}
          {p === current ? (
            <strong>{p}</strong>
          ) : (
            <a href={`/-/persona?as=${p}&next=${encodeURIComponent(pathname)}`}>{p}</a>
          )}
        </span>
      ))}
    </nav>
  );
}
