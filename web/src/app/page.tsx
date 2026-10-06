import { SANDBOX_REPO } from "@/lib/config";
import { GATED_REPOS_PATH } from "@/lib/gatedRepos";

// Web-app index (no HF equivalent): entry points to the sandbox repo screens.
export default function Home() {
  return (
    <main>
      <h1>Gated models replica</h1>
      <ul>
        <li>
          Model page (requester gate box): <a href={`/${SANDBOX_REPO}`}>/{SANDBOX_REPO}</a>
        </li>
        <li>
          Owner settings (Gated user access): <a href={`/${SANDBOX_REPO}/settings`}>/{SANDBOX_REPO}/settings</a>
        </li>
        <li>
          Requester&apos;s access requests (Gated Repos Status, self-cancel):{" "}
          <a href={GATED_REPOS_PATH}>{GATED_REPOS_PATH}</a>
        </li>
      </ul>
    </main>
  );
}
