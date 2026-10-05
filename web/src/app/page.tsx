import { SANDBOX_REPO } from "@/lib/config";

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
      </ul>
    </main>
  );
}
