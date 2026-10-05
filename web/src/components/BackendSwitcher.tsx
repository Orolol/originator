"use client";
// Links to `/-/backend?to=…&next=<current path>`; shows which backend answers this page.
import { usePathname } from "next/navigation";
import { BACKEND_IDS, BACKENDS, type BackendId } from "@/lib/backends";

export function BackendSwitcher({ current, pinnedUrl }: { current: BackendId; pinnedUrl: string | null }) {
  const pathname = usePathname() ?? "/";
  if (pinnedUrl) {
    return (
      <span aria-label="Backend">
        Backend: <strong>pinned</strong> to <code>{pinnedUrl}</code> (BACKEND_URL)
      </span>
    );
  }
  return (
    <nav aria-label="Switch backend">
      Backend:{" "}
      {BACKEND_IDS.map((b, i) => (
        <span key={b}>
          {i > 0 && " | "}
          {b === current ? (
            <strong>{b}</strong>
          ) : (
            <a href={`/-/backend?to=${b}&next=${encodeURIComponent(pathname)}`}>{b}</a>
          )}
        </span>
      ))}{" "}
      <small className={current === "bridge" ? "backend-live" : undefined}>({BACKENDS[current].note})</small>
    </nav>
  );
}
