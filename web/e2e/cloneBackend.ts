// Safety guard shared by `playwright.clone.config.ts` and `clone-walkthrough.spec.ts`: the clone
// walkthrough WRITES (it resets the backend state and clicks every owner control), so it may only
// ever target a local clone, never the bridge (8100, which fronts the live Hub) or anything else.
// The spec additionally checks that the backend answers `/__clone__/health`.
const CLONE_URL = /^http:\/\/127\.0\.0\.1:82\d\d$/;

export function assertCloneBackendUrl(url: string | undefined): string {
  const clean = (url ?? "").replace(/\/+$/, "");
  if (!CLONE_URL.test(clean) || clean.endsWith(":8100")) {
    throw new Error(
      `Refusing to run the clone walkthrough: BACKEND_URL=${JSON.stringify(url)} is not a local clone ` +
        "(expected http://127.0.0.1:82xx, for example http://127.0.0.1:8201). It writes to the backend.",
    );
  }
  return clean;
}
