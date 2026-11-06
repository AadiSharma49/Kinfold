"use client";

import { useCallback, useEffect, useState } from "react";
import { Section, SectionHeading } from "@/components/section";
import { ConnectKeyForm } from "@/components/connect-key-form";
import { CreateAgentForm } from "@/components/dashboard/create-agent-form";
import { AgentList } from "@/components/dashboard/agent-list";
import { KeyReveal } from "@/components/dashboard/key-reveal";
import { ConnectConfig } from "@/components/dashboard/connect-config";
import { DeleteAccountSection } from "@/components/dashboard/delete-account-section";
import { ownerFetch, useOwnerSession } from "@/lib/client-owner";
import type { Agent, ApiKey, ApiKeyCreated } from "@/lib/kinfold-api";

export default function DashboardPage() {
  const { connected, keyPrefix, connect, disconnect } = useOwnerSession();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [justCreated, setJustCreated] = useState<ApiKeyCreated | null>(null);

  const refresh = useCallback(async () => {
    const [agentsResponse, keysResponse] = await Promise.all([
      ownerFetch("/api/owners/me/agents"),
      ownerFetch("/api/keys"),
    ]);
    if (agentsResponse.ok) setAgents(await agentsResponse.json());
    if (keysResponse.ok) setKeys(await keysResponse.json());
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!connected) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [connected, refresh]);

  async function handleDisconnect() {
    await disconnect();
    setAgents([]);
    setKeys([]);
    setJustCreated(null);
    setLoaded(false);
  }

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
          <ConnectKeyForm
            connectedAs={keyPrefix}
            onConnect={connect}
            onDisconnect={handleDisconnect}
          />
        </div>

        {!connected && (
          <p className="mt-4 text-sm text-muted-foreground">
            Sign in with GitHub above to manage your agents.
          </p>
        )}

        {connected && (
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
              onCreated={(key) => {
                setJustCreated(key);
                void refresh();
              }}
            />

            <div>
              <p className="mb-3 text-sm font-medium">Your agents</p>
              {loaded ? (
                <AgentList
                  agents={agents}
                  keysByAgent={keysByAgent}
                  onKeyMinted={(_agentId, key) => {
                    setJustCreated(key);
                    void refresh();
                  }}
                  onKeyRevoked={() => void refresh()}
                />
              ) : (
                <p className="text-sm text-muted-foreground">Loading...</p>
              )}
            </div>

            <DeleteAccountSection
              onDeleted={() => {
                void handleDisconnect();
              }}
            />
          </div>
        )}
      </Section>
    </>
  );
}
