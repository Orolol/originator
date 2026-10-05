import type { Metadata } from "next";
import Link from "next/link";
import { backendJson, currentPersona, type WhoAmI } from "@/lib/backend";
import { PersonaSwitcher } from "@/components/PersonaSwitcher";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gated models (HF replica)",
  description: "Behaviour-faithful replica of Hugging Face gated-model screens",
};

export const dynamic = "force-dynamic";

async function ActingAs() {
  const persona = await currentPersona();
  const who = persona === "anonymous" ? null : await backendJson<WhoAmI>("/api/whoami-v2");
  return (
    <header className="persona-bar">
      <Link href="/">Home</Link> · Acting as <strong>{persona}</strong>
      {who?.ok && who.data?.name ? <> ({who.data.name})</> : null}
      {who && !who.ok ? <> (whoami: {who.error.status} {who.error.message})</> : null}
      {" · "}
      <PersonaSwitcher current={persona} />
    </header>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ActingAs />
        {children}
      </body>
    </html>
  );
}
