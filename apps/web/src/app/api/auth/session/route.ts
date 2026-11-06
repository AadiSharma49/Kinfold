import { NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/kinfold-api";
import {
  createOwnerSession,
  destroyOwnerSession,
  looksLikeOwnerKey,
  readOwnerKey,
} from "@/lib/owner-session";

export async function GET() {
  const key = await readOwnerKey();
  return NextResponse.json(
    {
      connected: Boolean(key),
      key_prefix: key ? `${key.slice(0, 12)}...` : null,
    },
    { headers: { "Cache-Control": "no-store" } }
  );
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const key = typeof body?.key === "string" ? body.key.trim() : "";

  if (!looksLikeOwnerKey(key)) {
    return NextResponse.json(
      { detail: "That does not look like a Kinfold owner key." },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(`${apiBaseUrl()}/v1/owners/me`, {
      headers: { Authorization: `Bearer ${key}` },
      cache: "no-store",
    });
    if (!response.ok) {
      return NextResponse.json(
        { detail: "That key was rejected. Check it and try again." },
        { status: 401 }
      );
    }
  } catch {
    return NextResponse.json(
      { detail: "Can't reach the Kinfold backend right now." },
      { status: 503 }
    );
  }

  await createOwnerSession(key);
  return NextResponse.json(
    { connected: true },
    { headers: { "Cache-Control": "no-store" } }
  );
}

export async function DELETE() {
  await destroyOwnerSession();
  return new NextResponse(null, { status: 204 });
}
