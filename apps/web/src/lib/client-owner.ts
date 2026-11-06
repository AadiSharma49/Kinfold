"use client";

import { useEffect, useSyncExternalStore } from "react";
import {
  CSRF_COOKIE,
  CSRF_HEADER,
  LEGACY_KEY_STORAGE,
  POST_LOGIN_REDIRECT_KEY,
} from "@/lib/session-cookies";

export type SessionResult =
  | { ok: true }
  | { ok: false; error: string; retryable: boolean };

type Snapshot = { connected: boolean; keyPrefix: string | null };

const EMPTY: Snapshot = { connected: false, keyPrefix: null };
let snapshot: Snapshot = EMPTY;
let loadPromise: Promise<void> | null = null;
const listeners = new Set<() => void>();

function emit(next: Snapshot) {
  snapshot = next;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot() {
  return snapshot;
}

function getServerSnapshot() {
  return EMPTY;
}

export function readCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function withCsrf(headers: HeadersInit | undefined, method: string): Headers {
  const result = new Headers(headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    const token = readCsrfToken();
    if (token) result.set(CSRF_HEADER, token);
  }
  return result;
}

/** Same-origin fetch that attaches the CSRF header for mutating requests. */
export async function ownerFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    headers: withCsrf(init.headers, init.method ?? "GET"),
  });
  if (response.status === 401) {
    // The proxy also clears the cookie; update this tab immediately.
    emit(EMPTY);
  }
  return response;
}

async function refreshOwnerSession(): Promise<void> {
  try {
    const response = await fetch("/api/auth/session", { cache: "no-store" });
    const data = await response.json().catch(() => null);
    emit({
      connected: Boolean(data?.connected),
      keyPrefix: typeof data?.key_prefix === "string" ? data.key_prefix : null,
    });
  } catch {
    emit(EMPTY);
  }
}

async function saveOwnerSession(key: string): Promise<SessionResult> {
  try {
    const response = await fetch("/api/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      return {
        ok: false,
        error: data?.detail ?? data?.message ?? "That key didn't work.",
        retryable: response.status >= 500,
      };
    }
    return { ok: true };
  } catch {
    return {
      ok: false,
      error: "Can't reach the server right now.",
      retryable: true,
    };
  }
}

async function loadOnce(): Promise<void> {
  let legacy: string | null = null;
  try {
    legacy = localStorage.getItem(LEGACY_KEY_STORAGE);
  } catch {
    legacy = null;
  }

  if (legacy) {
    const result = await saveOwnerSession(legacy);
    // Drop the old value when the migration worked or the key was
    // rejected outright; keep it only when the backend was unreachable.
    if (result.ok || !result.retryable) {
      try {
        localStorage.removeItem(LEGACY_KEY_STORAGE);
      } catch {
        // Storage can be unavailable (private modes); the cookie is enough.
      }
    }
  }

  await refreshOwnerSession();
}

export function ensureOwnerSessionLoaded(): Promise<void> {
  if (!loadPromise) loadPromise = loadOnce();
  return loadPromise;
}

/** Validates a raw owner key with the API, then stores it in an HttpOnly cookie. */
export async function signInOwner(rawKey: string): Promise<SessionResult> {
  const result = await saveOwnerSession(rawKey);
  if (result.ok) {
    try {
      localStorage.removeItem(LEGACY_KEY_STORAGE);
    } catch {
      // Storage can be unavailable; the cookie is enough.
    }
    await refreshOwnerSession();
  }
  return result;
}

export async function signOutOwner(): Promise<void> {
  try {
    await ownerFetch("/api/auth/session", { method: "DELETE" });
  } catch {
    // Clearing the local view below is still the right behavior.
  }
  try {
    localStorage.removeItem(LEGACY_KEY_STORAGE);
  } catch {
    // Storage can be unavailable; the cookie is already cleared server-side.
  }
  emit(EMPTY);
}

export function rememberPostLoginRedirect(path: string) {
  try {
    sessionStorage.setItem(POST_LOGIN_REDIRECT_KEY, path);
  } catch {
    // No sessionStorage means the callback falls back to /duels.
  }
}

export function takePostLoginRedirect(): string {
  try {
    const target = sessionStorage.getItem(POST_LOGIN_REDIRECT_KEY) ?? "/duels";
    sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
    return target;
  } catch {
    return "/duels";
  }
}

export function useOwnerSession() {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    void ensureOwnerSessionLoaded();
  }, []);

  return {
    connected: state.connected,
    keyPrefix: state.keyPrefix,
    connect: signInOwner,
    disconnect: signOutOwner,
    refresh: refreshOwnerSession,
  };
}
