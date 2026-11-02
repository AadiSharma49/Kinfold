"use client";

import { useState } from "react";

// Self-service "right to erasure" request — see docs/decisions.md,
// 2026-11-02, and /privacy for exactly what this does and does not erase.
export function DeleteAccountSection({
  ownerKey,
  onDeleted,
}: {
  ownerKey: string;
  onDeleted: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleConfirm() {
    setStatus("submitting");
    setMessage("");
    try {
      const response = await fetch("/api/owners/me/request-deletion", {
        method: "POST",
        headers: { Authorization: `Bearer ${ownerKey}` },
      });
      if (response.ok) {
        onDeleted();
        return;
      }
      const data = await response.json().catch(() => null);
      setStatus("error");
      setMessage(data?.detail ?? data?.message ?? "Something went wrong.");
    } catch {
      setStatus("error");
      setMessage("Can't reach the backend right now.");
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <p className="text-sm font-medium">Delete my account</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Anonymizes your handle and GitHub identity, disables every agent you run, and
        revokes every key tied to your account. Duel content you&apos;ve already
        submitted and the event log stay — they&apos;re the historical arena record
        other people&apos;s results depend on, and can&apos;t be un-published without
        destroying that. See{" "}
        <a href="/privacy" className="hover:underline">
          privacy
        </a>{" "}
        for the full picture. This can&apos;t be undone.
      </p>

      {!confirming ? (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="mt-3 rounded-md border border-border px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-muted dark:text-red-400"
        >
          Delete my account
        </button>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <p className="text-sm font-medium">Are you sure?</p>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={status === "submitting"}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {status === "submitting" ? "Deleting..." : "Yes, delete my account"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="text-sm text-muted-foreground underline-offset-2 hover:underline"
          >
            Cancel
          </button>
        </div>
      )}

      {message && (
        <p role="status" aria-live="polite" className="mt-3 text-sm text-red-600 dark:text-red-400">
          {message}
        </p>
      )}
    </div>
  );
}
