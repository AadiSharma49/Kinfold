import { proxyToApi } from "@/lib/api-proxy";

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyToApi(request, `/v1/keys/${id}`, { method: "DELETE" });
}
