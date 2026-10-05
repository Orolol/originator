"use client";
// "Add access" (manual mode, ui.md §B3): user search through quicksearch, then grant (REV-6).
// Provisional (Q-12): the dialog's layout, labels and confirmation are unrecorded. Here: one search
// box; clicking a result grants immediately (no confirmation step).
import { useEffect, useState } from "react";
import type { BackendError } from "@/lib/httpError";
import { searchUsers, type QuickSearchUser } from "@/lib/hubClient";
import { ErrorNotice } from "./ErrorNotice";

interface Props {
  error: BackendError | null;
  onGrant: (user: string) => void;
  onClose: () => void;
}

export function AddAccessDialog({ error, onGrant, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ q: string; users: QuickSearchUser[] }>({ q: "", users: [] });
  const [searchError, setSearchError] = useState<BackendError | null>(null);
  const q = query.trim();

  useEffect(() => {
    if (!q) return;
    const timer = setTimeout(async () => {
      const res = await searchUsers(q);
      if (res.ok) {
        setSearchError(null);
        setResults({ q, users: res.data });
      } else {
        setSearchError(res.error);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [q]);

  const users = q && results.q === q ? results.users : [];

  return (
    <div className="backdrop">
      <div role="dialog" aria-modal="true" aria-labelledby="add-access-title" className="dialog">
        <h2 id="add-access-title">Add access</h2>
        <button type="button" aria-label="Close" onClick={onClose} className="dialog-close">
          ×
        </button>
        <p>
          <label htmlFor="add-access-search">Username</label>{" "}
          <input id="add-access-search" type="search" value={query} onChange={(e) => setQuery(e.target.value)} />
        </p>
        <ErrorNotice error={searchError ?? error} />
        <ul>
          {users.map((u) => (
            <li key={u.user}>
              <button type="button" onClick={() => onGrant(u.user)}>
                {u.user}
              </button>{" "}
              {u.fullname}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
