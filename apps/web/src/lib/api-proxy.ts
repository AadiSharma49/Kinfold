import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { apiBaseUrl } from "@/lib/kinfold-api";
import { CSRF_COOKIE, CSRF_HEADER, OWNER_COOKIE } from "@/lib/session-cookies";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

// Browser JS never talks to apps/api directly — only this server-side
// proxy does — which sidesteps CORS and keeps the real API URL out of
// client bundles except where it's deliberately public (the GitHub
// sign-in link). Owner keys live in an HttpOnly cookie; agent keys are
// still passed through explicitly with an Authorization header.
export async function proxyToApi(
  request: Request,
  path: string,
  init: { method: string; body?: unknown } = { method: "GET" }
): Promise<NextResponse> {
  const auth = await resolveAuthorization(request, init.method);
  if (auth instanceof NextResponse) {
    return auth;
  }

  return forwardToApi(path, init, {
    authorization: auth.authorization,
    clearOn401: auth.fromCookie,
  });
}

// Public backend calls (for example the waitlist signup) need no key.
// The browser still goes through this server so the API URL stays out of
// client code and CORS stays off.
export async function proxyPublicToApi(
  path: string,
  init: { method: string; body?: unknown } = { method: "GET" }
): Promise<NextResponse> {
  return forwardToApi(path, init, {});
}

async function forwardToApi(
  path: string,
  init: { method: string; body?: unknown },
  options: { authorization?: string; clearOn401?: boolean }
): Promise<NextResponse> {
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      method: init.method,
      headers: {
        ...(options.authorization ? { Authorization: options.authorization } : {}),
        ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      cache: "no-store",
    });

    if (response.status === 401 && options.clearOn401) {
      // The owner key was revoked or the owner was deleted. Drop the
      // now-useless cookie so the UI can fall back to signed-out.
      const store = await cookies();
      store.delete(OWNER_COOKIE);
      store.delete(CSRF_COOKIE);
    }

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

type ResolvedAuth = { authorization: string; fromCookie: boolean };

async function resolveAuthorization(
  request: Request,
  method: string
): Promise<ResolvedAuth | NextResponse> {
  const header = request.headers.get("authorization");
  if (header) {
    // Agent keys arrive this way and are never stored in a cookie, so a
    // cross-site request can't forge them — no CSRF check needed.
    return { authorization: header, fromCookie: false };
  }

  const store = await cookies();
  const ownerKey = store.get(OWNER_COOKIE)?.value;
  if (!ownerKey) {
    return NextResponse.json(
      { status: "error", message: "Connect your Kinfold key first." },
      { status: 401 }
    );
  }

  if (MUTATING_METHODS.has(method.toUpperCase())) {
    const cookieToken = store.get(CSRF_COOKIE)?.value;
    const headerToken = request.headers.get(CSRF_HEADER);
    if (!cookieToken || !headerToken || cookieToken !== headerToken) {
      return NextResponse.json(
        {
          status: "error",
          message: "Security check failed. Reload the page and try again.",
        },
        { status: 403 }
      );
    }
  }

  return { authorization: `Bearer ${ownerKey}`, fromCookie: true };
}
