// Owner settings `/{ns}/{repo}/settings`, section "Gated user access" (ui.md §B).
import { ErrorNotice } from "@/components/ErrorNotice";
import { GatedUserAccess } from "@/components/GatedUserAccess";
import { backendJson, repoPath } from "@/lib/backend";
import type { AccessRequest, Gated } from "@/lib/hubClient";

export default async function SettingsPage({ params }: { params: Promise<{ ns: string; repo: string }> }) {
  const { ns, repo: name } = await params;
  const repoId = `${ns}/${name}`;
  const repo = repoPath(ns, name);
  const info = await backendJson<{ id?: string; gated?: Gated }>(`/api/models/${repo}`);
  if (!info.ok) {
    return (
      <main>
        <h1>{repoId}</h1>
        <ErrorNotice error={info.error} />
      </main>
    );
  }
  const pending = await backendJson<AccessRequest[]>(`/api/models/${repo}/user-access-request/pending`);
  // Provisional (Q-12): what HF shows a non-owner on this page is unrecorded. The owner list
  // endpoint answers 401 (anonymous) / 403 (no write permission, api.md §3.3) for them: show that
  // answer verbatim instead of the controls. Other failures (e.g. 400 on a non-gated repo) still
  // render the section, without a count.
  const denied = !pending.ok && (pending.error.status === 401 || pending.error.status === 403);

  return (
    <main>
      <h1>{info.data.id ?? repoId}</h1>
      <p>
        <a href={`/${repoId}`}>Model card</a>
      </p>
      <h2>Settings</h2>
      {denied ? (
        <ErrorNotice error={pending.ok ? null : pending.error} />
      ) : (
        <GatedUserAccess
          repoId={repoId}
          initialGated={info.data.gated ?? false}
          initialPendingCount={pending.ok && Array.isArray(pending.data) ? pending.data.length : null}
        />
      )}
    </main>
  );
}
