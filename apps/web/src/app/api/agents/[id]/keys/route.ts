import { proxyToApi } from "@/lib/api-proxy";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let body: unknown = {};
  try {
    body = await request.json();
  } catch {
    // No body sent is fine — label is optional.
  }
  return proxyToApi(request, `/v1/agents/${id}/keys`, { method: "POST", body: body ?? {} });
}
