import { NextResponse } from "next/server";
import { proxyPublicToApi } from "@/lib/api-proxy";
import { isRateLimited, waitlistSchema } from "@/lib/waitlist";

// Signups live in the FastAPI Postgres database. This route keeps the
// browser on the web origin, validates the shape, and applies a small
// per-instance rate limit before forwarding.
export async function POST(request: Request) {
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "unknown";

  if (isRateLimited(ip)) {
    return NextResponse.json(
      { status: "error", message: "Too many requests. Try again later." },
      { status: 429 }
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

  const parsed = waitlistSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { status: "error", message: "Please check the form and try again." },
      { status: 400 }
    );
  }

  // Honeypot: real users never fill this hidden field.
  if (parsed.data.company) {
    return NextResponse.json({ status: "ok" });
  }

  return proxyPublicToApi("/v1/waitlist", {
    method: "POST",
    body: parsed.data,
  });
}
