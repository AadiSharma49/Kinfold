import { NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/kinfold-api";

// Shared by every same-origin route under src/app/api/** that forwards a
// browser-held Kinfold key to the real backend. Browser JS never talks to
// apps/api directly — only this server-side proxy does — which sidesteps
// CORS and keeps the real API URL out of client bundles except where it's
// deliberately public (the GitHub sign-in link).
export async function proxyToApi(
  request: Request,
  path: string,
  init: { method: string; body?: unknown } = { method: "GET" }
): Promise<NextResponse> {
  const authorization = request.headers.get("authorization");
  if (!authorization) {
    return NextResponse.json(
      { status: "error", message: "Connect your Kinfold key first." },
      { status: 401 }
    );
  }

  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      method: init.method,
      headers: {
        Authorization: authorization,
        ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await response.json().catch(() => null);
    return NextResponse.json(
      data ?? { status: "error", message: "Unexpected response from the backend." },
      { status: response.status }
    );
  } catch {
    return NextResponse.json(
      { status: "error", message: "Can't reach the Kinfold backend right now." },
      { status: 503 }
    );
  }
}
