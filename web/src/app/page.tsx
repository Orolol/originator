import { currentBackend } from "@/lib/backend";
import { sandboxRepoFor } from "@/lib/config";

// Web-app index (no HF equivalent): entry points to the sandbox repo screens.
export default async function Home() {
  const SANDBOX_REPO = sandboxRepoFor(await currentBackend());
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
      </ul>
    </main>
  );
}
