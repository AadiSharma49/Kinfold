"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "kinfold_owner_key";
const API_BASE = process.env.NEXT_PUBLIC_KINFOLD_API_URL ?? "http://localhost:8000";

/** Used by /auth/callback after a GitHub login redirect delivers a key. */
export function setStoredKey(rawKey: string) {
  localStorage.setItem(STORAGE_KEY, rawKey);
}

export function useConnectedKey() {
  const [key, setKey] = useState<string | null>(null);

  useEffect(() => {
    // Reads from localStorage after mount on purpose: doing this during
    // render would crash on the server and reading it eagerly would cause
    // a hydration mismatch, since the server never has a stored key.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setKey(localStorage.getItem(STORAGE_KEY));
  }, []);

  function connect(rawKey: string) {
    localStorage.setItem(STORAGE_KEY, rawKey);
    setKey(rawKey);
  }

  function disconnect() {
    localStorage.removeItem(STORAGE_KEY);
    setKey(null);
  }

  return { key, connect, disconnect };
}

export function ConnectKeyForm({
  connectedKey,
  onConnect,
  onDisconnect,
}: {
  connectedKey: string | null;
  onConnect: (key: string) => void;
  onDisconnect: () => void;
}) {
  const [input, setInput] = useState("");
  const [showManual, setShowManual] = useState(false);

  if (connectedKey) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted px-3 py-2">
        <span className="font-mono text-xs text-muted-foreground">
          Connected as {connectedKey.slice(0, 12)}...
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

  return (
    <div className="flex flex-col gap-2">
      <a
        href={`${API_BASE}/v1/auth/github/login`}
        className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium transition-colors hover:bg-muted"
      >
        Sign in with GitHub
      </a>

      {showManual ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (input.trim()) onConnect(input.trim());
          }}
          className="flex flex-col gap-2 sm:flex-row"
        >
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
            className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted"
          >
            Connect
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
    </div>
  );
}
