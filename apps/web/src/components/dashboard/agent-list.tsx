"use client";

import { useState } from "react";
import type { Agent, ApiKey, ApiKeyCreated } from "@/lib/kinfold-api";

function KeyRow({
  apiKey,
  ownerKey,
  onRevoked,
}: {
  apiKey: ApiKey;
  ownerKey: string;
  onRevoked: (keyId: string) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function handleRevoke() {
    setBusy(true);
    try {
      const response = await fetch(`/api/keys/${apiKey.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${ownerKey}` },
      });
      if (response.ok) onRevoked(apiKey.id);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="flex items-center justify-between gap-3 text-xs">
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
    </li>
  );
}

export function AgentList({
  ownerKey,
  agents,
  keysByAgent,
  onKeyMinted,
  onKeyRevoked,
}: {
  ownerKey: string;
  agents: Agent[];
  keysByAgent: Record<string, ApiKey[]>;
  onKeyMinted: (agentId: string, key: ApiKeyCreated) => void;
  onKeyRevoked: (keyId: string) => void;
}) {
  const [mintingFor, setMintingFor] = useState<string | null>(null);

  async function handleMint(agentId: string) {
    setMintingFor(agentId);
    try {
      const response = await fetch(`/api/agents/${agentId}/keys`, {
        method: "POST",
        headers: { Authorization: `Bearer ${ownerKey}` },
        body: JSON.stringify({}),
      });
      const data = await response.json().catch(() => null);
      if (response.ok) onKeyMinted(agentId, data);
    } finally {
      setMintingFor(null);
    }
  }

  if (agents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No agents yet — create one above to get your first key.
      </p>
    );
  }

  return (
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
              <KeyRow key={k.id} apiKey={k} ownerKey={ownerKey} onRevoked={onKeyRevoked} />
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
