import { NextResponse } from "next/server";
import { proxyToApi } from "@/lib/api-proxy";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ status: "error", message: "Invalid request body." }, { status: 400 });
  }
  return proxyToApi(request, `/v1/duels/${id}/human-entry`, { method: "POST", body });
}
