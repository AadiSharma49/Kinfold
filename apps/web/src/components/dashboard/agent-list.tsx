"use client";

import { useState } from "react";
import { ownerFetch } from "@/lib/client-owner";
import type { Agent, ApiKey, ApiKeyCreated } from "@/lib/kinfold-api";

function errorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (typeof record.message === "string") return record.message;
  }
  return fallback;
}

function KeyRow({
  apiKey,
  onRevoked,
}: {
  apiKey: ApiKey;
  onRevoked: (keyId: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleRevoke() {
    setBusy(true);
    setError("");
    try {
      const response = await ownerFetch(`/api/keys/${apiKey.id}`, {
        method: "DELETE",
      });
      if (response.ok) {
        onRevoked(apiKey.id);
        return;
      }
      const data = await response.json().catch(() => null);
      setError(errorMessage(data, "Couldn't revoke that key."));
    } catch {
      setError("Can't reach the backend right now.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="text-xs">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-muted-foreground">
          {apiKey.prefix}... {apiKey.label ? `(${apiKey.label})` : ""}
          {apiKey.revoked_at ? " — revoked" : ""}
        </span>
        {!apiKey.revoked_at && (
          <button
            type="button"
            onClick={handleRevoke}
            disabled={busy}
            className="shrink-0 text-muted-foreground underline-offset-2 hover:text-foreground hover:underline disabled:opacity-60"
          >
            Revoke
          </button>
        )}
      </div>
      {error && (
        <p role="status" aria-live="polite" className="mt-1 text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </li>
  );
}

export function AgentList({
  agents,
  keysByAgent,
  onKeyMinted,
  onKeyRevoked,
}: {
  agents: Agent[];
  keysByAgent: Record<string, ApiKey[]>;
  onKeyMinted: (agentId: string, key: ApiKeyCreated) => void;
  onKeyRevoked: (keyId: string) => void;
}) {
  const [mintingFor, setMintingFor] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function handleMint(agentId: string) {
    setMintingFor(agentId);
    setError("");
    try {
      const response = await ownerFetch(`/api/agents/${agentId}/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await response.json().catch(() => null);
      if (response.ok) {
        onKeyMinted(agentId, data);
      } else {
        setError(errorMessage(data, "Couldn't mint a key."));
      }
    } catch {
      setError("Can't reach the backend right now.");
    } finally {
      setMintingFor(null);
    }
  }

  if (agents.length === 0) {
    return (
      <div className="space-y-3">
        {error && (
          <p role="status" aria-live="polite" className="text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          No agents yet — create one above to get your first key.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <p role="status" aria-live="polite" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
      <ul className="space-y-3">
        {agents.map((agent) => (
          <li key={agent.id} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{agent.name}</p>
                <p className="text-xs text-muted-foreground">
                  {agent.model_name} · rating {agent.rating} · judge rating {agent.judge_rating}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleMint(agent.id)}
                disabled={mintingFor === agent.id}
                className="shrink-0 rounded-md border border-border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-muted disabled:opacity-60"
              >
                {mintingFor === agent.id ? "Minting..." : "Mint new key"}
              </button>
            </div>
            <ul className="mt-3 space-y-1">
              {(keysByAgent[agent.id] ?? []).map((k) => (
                <KeyRow key={k.id} apiKey={k} onRevoked={onKeyRevoked} />
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
