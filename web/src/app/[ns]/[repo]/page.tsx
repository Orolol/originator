// Model page `/{ns}/{repo}` (ui.md §A): repo id, the gate box when gated and the persona has no
// access (or the "Gated model" block when it has), and the file list (public on gated repos, ACC-4)
// linking to `resolve`.
import { GateBox, GatedModelAccess } from "@/components/GateBox";
import { ErrorNotice } from "@/components/ErrorNotice";
import { backendJson, fetchGateState, repoPath, type WhoAmI } from "@/lib/backend";
import { gateConfigFromCardData } from "@/lib/gateForm";
import type { Gated } from "@/lib/hubClient";

interface ModelInfo {
  id: string;
  gated?: Gated;
  cardData?: unknown;
  siblings?: { rfilename: string }[];
}

function resolveHref(repoId: string, path: string): string {
  return `/${repoId}/resolve/main/${path.split("/").map(encodeURIComponent).join("/")}`;
}

export default async function ModelPage({ params }: { params: Promise<{ ns: string; repo: string }> }) {
  const { ns, repo: name } = await params;
  const repoId = `${ns}/${name}`;
  const repo = repoPath(ns, name);
  const info = await backendJson<ModelInfo>(`/api/models/${repo}`);
  if (!info.ok) {
    return (
      <main>
        <h1>{repoId}</h1>
        <ErrorNotice error={info.error} />
      </main>
    );
  }
  const model = info.data;
  // CFG-5 / ACC-7: no gate (and extra_gated_* ignored) while gated == false.
  // ACC-1: the owner's auth-check is 200, so the owner sees the "Gated model" block, not the gate box
  // [OBS-UI 2026-10-06]; an accepted requester gets the same answer (Provisional (Q-11), see GatedModelAccess).
  const gate = model.gated ? await fetchGateState(repo) : null;
  const who = await backendJson<WhoAmI>("/api/whoami-v2");
  const canManage =
    who.ok && (who.data?.name === ns || (who.data?.orgs ?? []).some((org) => org.name === ns));
  const files = (model.siblings ?? []).map((s) => s.rfilename);

  return (
    <main>
      <h1>{model.id ?? repoId}</h1>
      {canManage && (
        <nav aria-label="Repository">
          {/* Provisional (Q-12): settings link shown when whoami names the namespace (owner or org member). */}
          <a href={`/${repoId}/settings`}>Settings</a>
        </nav>
      )}
      {gate && model.gated && gate.kind === "access" && <GatedModelAccess />}
      {gate && model.gated && gate.kind !== "access" && (
        <GateBox repoId={repoId} config={gateConfigFromCardData(model.cardData)} state={gate} mode={model.gated} />
      )}
      <section aria-labelledby="files-heading">
        <h2 id="files-heading">Files</h2>
        <ul>
          {files.map((path) => (
            <li key={path}>
              <a href={resolveHref(repoId, path)}>{path}</a>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
