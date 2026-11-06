"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signInOwner, takePostLoginRedirect } from "@/lib/client-owner";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"working" | "error">("working");

  const [login] = useState<{ key: string | null; error: string | null }>(() => {
    if (typeof window === "undefined") return { key: null, error: null };
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    return { key: hash.get("key"), error: hash.get("error") };
  });

  useEffect(() => {
    if (!login.key) {
      // No key and no error means someone opened /auth/callback directly.
      // Nothing can be signed in here, so show the same recovery link.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatus("error");
      return;
    }

    // Drop the key from the address bar and history before doing anything
    // else, so it can't leak through a refresh or a copied URL.
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search
    );

    let cancelled = false;
    void signInOwner(login.key).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        router.replace(takePostLoginRedirect());
      } else {
        setStatus("error");
      }
    });

    return () => {
      cancelled = true;
    };
  }, [login, router]);

  return (
    <div className="content-width flex flex-1 items-center justify-center py-24 text-center">
      {status === "working" ? (
        <p className="text-muted-foreground">Signing you in...</p>
      ) : (
        <div>
          <p className="text-muted-foreground">
            Something went wrong signing in with GitHub. Try again.
          </p>
          <Link
            href="/duels"
            className="mt-3 inline-block text-sm text-accent underline-offset-2 hover:underline"
          >
            Back to duels
          </Link>
        </div>
      )}
    </div>
  );
}
