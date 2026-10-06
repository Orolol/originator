// Dialog flags in the page URL: HF's settings page adds `?gated_access_request=true` while the review
// modal is open and `?gated_add_user=true` while "Add access" is open, and removes them on close
// [OBS-UI 2026-10-06]. Provisional (Q-13): whether HF pushes or replaces the history entry, and whether
// loading a URL with the flag opens the dialog, is unrecorded; we replace the entry and only mirror the
// open state.

export function setUrlFlag(name: string, on: boolean): void {
  const url = new URL(window.location.href);
  if (on === (url.searchParams.get(name) === "true")) return;
  if (on) url.searchParams.set(name, "true");
  else url.searchParams.delete(name);
  window.history.replaceState(null, "", url);
}
