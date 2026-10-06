// `/settings/gated-repos`, "Gated Repos Status" [OBS-UI 2026-10-06]: the requester's access requests
// and HF's self-cancel control (REQ-7). HF renders it from server props listing every repo the user
// requested; our backends have no "my requests" endpoint, so the rows are derived from auth-check for
// the repos this web app knows (SANDBOX_REPO), through lib/gateState.
import { ErrorNotice } from "@/components/ErrorNotice";
import { GatedReposTable } from "@/components/GatedReposTable";
import { fetchGateState, repoPath } from "@/lib/backend";
import { SANDBOX_REPO } from "@/lib/config";
import type { GatedRepoRow } from "@/lib/gatedRepos";
import { gatedRepoRequestStatus } from "@/lib/gateState";
import type { BackendError } from "@/lib/httpError";

/** Repos whose request status this page can show (rows only exist for repos the web app knows). */
const KNOWN_REPOS = [SANDBOX_REPO];

export default async function GatedReposPage() {
  const rows: GatedRepoRow[] = [];
  const errors: BackendError[] = [];
  for (const repo of KNOWN_REPOS) {
    const [ns, name] = repo.split("/");
    const state = await fetchGateState(repoPath(ns, name));
    const status = gatedRepoRequestStatus(state);
    if (status) rows.push({ repo, type: "model", date: null, status });
    // docs/system.md: an answer lib/gateState cannot map is shown verbatim, never guessed.
    else if (state.kind === "unmapped") errors.push({ status: state.status, code: state.code, message: state.message });
  }
  return (
    <main>
      <h1>Gated Repos Status</h1>
      <p>View the gated repositories that you have requested access to.</p>
      {errors.map((error, i) => (
        <ErrorNotice key={i} error={error} />
      ))}
      <GatedReposTable rows={rows} />
    </main>
  );
}
