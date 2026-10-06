"use client";
// "Add access" (manual mode, ui.md §B3) [OBS-UI 2026-10-06]: a native <dialog> titled "Add a user
// access manually" that adds `?gated_add_user=true` to the URL while open. It searches users with
// `GET /api/quicksearch?q=&type=user` on open, then `?q=<text>&type=user` while typing (debounced);
// picking a result only selects it, and the separate "Grant access" button, disabled until a user is
// chosen, grants (REV-6). An empty result shows "No results found :(" (HF's own search finds nobody,
// Q-25).
import { useEffect, useRef, useState } from "react";
import type { BackendError } from "@/lib/httpError";
import { searchUsers, type QuickSearchUser } from "@/lib/hubClient";
import { setUrlFlag } from "@/lib/urlFlag";
import { ErrorNotice } from "./ErrorNotice";

// [OBS-UI 2026-10-06] typing fires a debounced request; the delay itself is not measured.
export const USER_SEARCH_DEBOUNCE_MS = 300;

interface Props {
  error: BackendError | null;
  onGrant: (user: string) => void;
  onClose: () => void;
}

export function AddAccessDialog({ error, onGrant, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ q: string; users: QuickSearchUser[] } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<BackendError | null>(null);
  const q = query.trim();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    setUrlFlag("gated_add_user", true);
    return () => setUrlFlag("gated_add_user", false);
  }, []);

  useEffect(() => {
    // The empty query (dialog just opened, or field cleared) goes out at once, typing is debounced.
    const timer = setTimeout(
      async () => {
        const res = await searchUsers(q);
        if (res.ok) {
          setSearchError(null);
          setResults({ q, users: res.data });
        } else {
          setSearchError(res.error);
        }
      },
      q ? USER_SEARCH_DEBOUNCE_MS : 0,
    );
    return () => clearTimeout(timer);
  }, [q]);

  const users = results && results.q === q ? results.users : null;

  return (
    <dialog ref={dialogRef} aria-labelledby="add-access-title" className="dialog" onClose={onClose}>
      <h2 id="add-access-title">Add a user access manually</h2>
      <button type="button" aria-label="Close" onClick={() => dialogRef.current?.close()} className="dialog-close">
        <span aria-hidden="true">×</span>
      </button>
      <p>
        <input
          type="text"
          placeholder="Start typing to search for a user"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            // Provisional (Q-12): a new search clears the choice (HF's selection UI was never shown,
            // its search returned nobody).
            setSelected(null);
          }}
        />
      </p>
      <ErrorNotice error={searchError ?? error} />
      {users && users.length === 0 && <p>No results found :(</p>}
      {users && users.length > 0 && (
        <ul>
          {users.map((u) => (
            <li key={u.user}>
              {/* Provisional (Q-12): a result is a toggle button; aria-pressed marks the chosen user. */}
              <button type="button" aria-pressed={selected === u.user} onClick={() => setSelected(u.user)}>
                {u.user}
              </button>{" "}
              {u.fullname}
            </li>
          ))}
        </ul>
      )}
      <button type="button" disabled={selected === null} onClick={() => selected && onGrant(selected)}>
        Grant access
      </button>
    </dialog>
  );
}
