// How the Hub reports errors (docs/hf-gated/api.md §3): `X-Error-Code` / `X-Error-Message`
// headers, plus a JSON `{"error": …}` body on /api routes or a text/plain body on web routes.
// Shared by server components and browser code.

export interface BackendError {
  status: number;
  code: string | null;
  message: string;
}

export async function readBackendError(res: Response): Promise<BackendError> {
  const code = res.headers.get("x-error-code");
  let message = res.headers.get("x-error-message") ?? "";
  if (!message) {
    const text = await res.text().catch(() => "");
    message = text;
    try {
      const parsed: unknown = JSON.parse(text);
      if (parsed && typeof parsed === "object" && typeof (parsed as { error?: unknown }).error === "string") {
        message = (parsed as { error: string }).error;
      }
    } catch {
      // not JSON: keep the text body verbatim
    }
  }
  return { status: res.status, code, message };
}

export type ApiResult<T> = { ok: true; status: number; data: T } | { ok: false; error: BackendError };

/** Parses a JSON (or empty / text) success body, or the error triple on a non-2xx status. */
export async function toApiResult<T>(res: Response): Promise<ApiResult<T>> {
  if (!res.ok) return { ok: false, error: await readBackendError(res) };
  const text = await res.text();
  let data: unknown = text;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // keep text
    }
  } else {
    data = null;
  }
  return { ok: true, status: res.status, data: data as T };
}
