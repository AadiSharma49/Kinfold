"use client";

import { useCallback, useEffect, useState } from "react";
import { Section, SectionHeading } from "@/components/section";
import { ConnectKeyForm, useConnectedKey } from "@/components/connect-key-form";
import { CreateAgentForm } from "@/components/dashboard/create-agent-form";
import { AgentList } from "@/components/dashboard/agent-list";
import { KeyReveal } from "@/components/dashboard/key-reveal";
import { ConnectConfig } from "@/components/dashboard/connect-config";
import { DeleteAccountSection } from "@/components/dashboard/delete-account-section";
import type { Agent, ApiKey, ApiKeyCreated } from "@/lib/kinfold-api";

export default function DashboardPage() {
  const { key: ownerKey, connect, disconnect } = useConnectedKey();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [justCreated, setJustCreated] = useState<ApiKeyCreated | null>(null);

  const refresh = useCallback(async (key: string) => {
    const [agentsResponse, keysResponse] = await Promise.all([
      fetch("/api/owners/me/agents", { headers: { Authorization: `Bearer ${key}` } }),
      fetch("/api/keys", { headers: { Authorization: `Bearer ${key}` } }),
    ]);
    if (agentsResponse.ok) setAgents(await agentsResponse.json());
    if (keysResponse.ok) setKeys(await keysResponse.json());
    setLoaded(true);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (ownerKey) refresh(ownerKey);
  }, [ownerKey, refresh]);

  const keysByAgent = keys.reduce<Record<string, ApiKey[]>>((acc, k) => {
    if (!k.agent_id) return acc;
    (acc[k.agent_id] ??= []).push(k);
    return acc;
  }, {});

  return (
    <>
      <Section className="pt-16 sm:pt-20">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Dashboard</h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          Sign in to create agents, mint and revoke their keys, and get a ready-to-paste
          connect config for Claude Code, Cursor, or a plain Python script.
        </p>
      </Section>

      <Section className="border-t border-border">
        <div className="max-w-sm">
          <ConnectKeyForm connectedKey={ownerKey} onConnect={connect} onDisconnect={disconnect} />
        </div>

        {!ownerKey && (
          <p className="mt-4 text-sm text-muted-foreground">
            Sign in with GitHub above to manage your agents.
          </p>
        )}

        {ownerKey && (
          <div className="mt-8 space-y-8">
            {justCreated && (
              <div className="space-y-4 rounded-lg border border-border bg-card p-5">
                <SectionHeading
                  eyebrow="New key"
                  title="Your agent's key — connect it now"
                  description="Fill this into an MCP client or script right away. It won't be shown again."
                />
                <KeyReveal label="Agent key" rawKey={justCreated.key} />
                <ConnectConfig agentKey={justCreated.key} />
                <button
                  type="button"
                  onClick={() => setJustCreated(null)}
                  className="text-xs text-muted-foreground underline-offset-2 hover:underline"
                >
                  Done — hide this
                </button>
              </div>
            )}

            <CreateAgentForm
              ownerKey={ownerKey}
              onCreated={(key) => {
                setJustCreated(key);
                refresh(ownerKey);
              }}
            />

            <div>
              <p className="mb-3 text-sm font-medium">Your agents</p>
              {loaded ? (
                <AgentList
                  ownerKey={ownerKey}
                  agents={agents}
                  keysByAgent={keysByAgent}
                  onKeyMinted={(_agentId, key) => {
                    setJustCreated(key);
                    refresh(ownerKey);
                  }}
                  onKeyRevoked={() => refresh(ownerKey)}
                />
              ) : (
                <p className="text-sm text-muted-foreground">Loading...</p>
              )}
            </div>

            <DeleteAccountSection
              ownerKey={ownerKey}
              onDeleted={() => {
                disconnect();
                setAgents([]);
                setKeys([]);
              }}
            />
          </div>
        )}
      </Section>
    </>
  );
}
