import { cookies } from "next/headers";
import {
  CSRF_COOKIE,
  OWNER_COOKIE,
  SESSION_MAX_AGE_SECONDS,
} from "@/lib/session-cookies";

const isProduction = process.env.NODE_ENV === "production";

export function looksLikeOwnerKey(value: string): boolean {
  return /^kf_owner_[A-Za-z0-9_-]{20,}$/.test(value);
}

export async function readOwnerKey(): Promise<string | null> {
  const store = await cookies();
  return store.get(OWNER_COOKIE)?.value ?? null;
}

export async function createOwnerSession(key: string): Promise<void> {
  const store = await cookies();

  store.set(OWNER_COOKIE, key, {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
  store.set(CSRF_COOKIE, crypto.randomUUID(), {
    httpOnly: false,
    secure: isProduction,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
}

export async function destroyOwnerSession(): Promise<void> {
  const store = await cookies();
  store.delete(OWNER_COOKIE);
  store.delete(CSRF_COOKIE);
}
