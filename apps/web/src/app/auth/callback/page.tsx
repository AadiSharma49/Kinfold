"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { setStoredKey } from "@/components/connect-key-form";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"working" | "error">("working");

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const key = hash.get("key");
    const error = hash.get("error");

    if (key) {
      setStoredKey(key);
      router.replace("/duels");
      return;
    }

    if (error) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatus("error");
    }
  }, [router]);

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
