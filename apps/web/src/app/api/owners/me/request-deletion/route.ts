import { proxyToApi } from "@/lib/api-proxy";

export async function POST(request: Request) {
  return proxyToApi(request, "/v1/owners/me/request-deletion", { method: "POST" });
}
