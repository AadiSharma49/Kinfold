import { proxyToApi } from "@/lib/api-proxy";

// Used by the dashboard's "test connection" button — the browser calls this
// with the just-minted agent key in the Authorization header, same as any
// real agent would, to prove the key actually works end to end.
export async function GET(request: Request) {
  return proxyToApi(request, "/v1/agents/me");
}
