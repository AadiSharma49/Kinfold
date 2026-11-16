"use client";

import { useState } from "react";
import type { SessionResult } from "@/lib/client-owner";
import { rememberPostLoginRedirect } from "@/lib/client-owner";
import { publicApiBaseUrl } from "@/lib/public-api-url";

const API_BASE = publicApiBaseUrl();

export function ConnectKeyForm({
  connectedAs,
  onConnect,
  onDisconnect,
}: {
  connectedAs: string | null;
  onConnect: (key: string) => Promise<SessionResult>;
  onDisconnect: () => void | Promise<void>;
}) {
  const [input, setInput] = useState("");
  const [showManual, setShowManual] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (connectedAs) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted px-3 py-2">
        <span className="font-mono text-xs text-muted-foreground">
          Connected as {connectedAs}
        </span>
        <button
          type="button"
          onClick={onDisconnect}
          className="text-xs text-muted-foreground underline-offset-2 hover:underline"
        >
          Disconnect
        </button>
      </div>
    );
  }

  async function handleManualSubmit(event: React.FormEvent) {
    event.preventDefault();
    const value = input.trim();
    if (!value || submitting) return;

    setSubmitting(true);
    setError("");
    const result = await onConnect(value);
    if (result.ok) {
      setInput("");
    } else {
      setError(result.error);
    }
    setSubmitting(false);
  }

  return (
    <div className="flex flex-col gap-2">
      <a
        href={`${API_BASE}/v1/auth/github/login`}
        onClick={() => {
          // Remembered here, read back by /auth/callback — otherwise
          // signing in from anywhere but the duels page dumps you back on
          // /duels instead of where you actually started.
          rememberPostLoginRedirect(window.location.pathname);
        }}
        className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium transition-colors hover:bg-muted"
      >
        Sign in with GitHub
      </a>

      {showManual ? (
        <form onSubmit={handleManualSubmit} className="flex flex-col gap-2 sm:flex-row">
          <label htmlFor="kinfold-key" className="sr-only">
            Your Kinfold owner key
          </label>
          <input
            id="kinfold-key"
            type="password"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="kf_owner_..."
            autoComplete="off"
            className="flex-1 rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-60"
          >
            {submitting ? "Connecting..." : "Connect"}
          </button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setShowManual(true)}
          className="self-start text-xs text-muted-foreground underline-offset-2 hover:underline"
        >
          Or paste a key manually
        </button>
      )}

      {error && (
        <p role="status" aria-live="polite" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
