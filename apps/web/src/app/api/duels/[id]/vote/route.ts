import { NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/kinfold-api";

// Thin proxy to the real backend: the browser never talks to apps/api
// directly, it talks to this same-origin route, which forwards the
// Authorization header the browser sent (the viewer's own Kinfold key,
// pasted into the connect-key form and stored only in their browser).
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const authorization = request.headers.get("authorization");
  if (!authorization) {
    return NextResponse.json(
      { status: "error", message: "Connect your Kinfold key first." },
      { status: 401 }
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { status: "error", message: "Invalid request body." },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(`${apiBaseUrl()}/v1/duels/${id}/vote`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authorization,
      },
      body: JSON.stringify(body),
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
