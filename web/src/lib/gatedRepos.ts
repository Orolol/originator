// `/settings/gated-repos`, "Gated Repos Status" (HF component `UserSettingsGatedRepos`
// [OBS-UI 2026-10-06]): the requester's own access requests, where HF puts the self-cancel control.
// Shared by the server page and the client table.
import type { GatedRepoRequestStatus } from "./gateState";

export const GATED_REPOS_PATH = "/settings/gated-repos";

export interface GatedRepoRow {
  /** `{ns}/{name}`, linked to the repo page. */
  repo: string;
  /** Only models are in the slice; HF shows `model`. */
  type: "model";
  /** HF shows the submission date (`Oct 6`, from `submittedAt`). Provisional (Q-3): the API does not expose it to the requester, so it is null (empty cell). */
  date: string | null;
  status: GatedRepoRequestStatus;
}
