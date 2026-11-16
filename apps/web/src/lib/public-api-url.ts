// Base URL of the Kinfold API for code that runs in the browser: the
// "Sign in with GitHub" link and the example MCP config on the dashboard.
// NEXT_PUBLIC_* vars are inlined into the client bundle at build time, so
// this reads only that var — the server-only KINFOLD_API_URL (lib/
// kinfold-api.ts) is invisible in the browser and must not be used there.
// Both default to the local API in dev and are set to the same value in
// production — see docs/deploy-checklist.md step 10.
export function publicApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_KINFOLD_API_URL ?? "http://localhost:8000";
}
