import type { BackendError } from "@/lib/httpError";

// Provisional (Q-9, Q-12): how HF's UI words backend errors is unrecorded; we show the backend's
// status, X-Error-Code and message verbatim.
export function ErrorNotice({ error }: { error: BackendError | null }) {
  if (!error) return null;
  return (
    <p role="alert">
      {error.status} {error.code ? `${error.code}: ` : ""}
      {error.message}
    </p>
  );
}
