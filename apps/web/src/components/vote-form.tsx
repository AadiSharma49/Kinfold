"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConnectKeyForm } from "@/components/connect-key-form";
import { ownerFetch, useOwnerSession } from "@/lib/client-owner";
import type { DuelEntry } from "@/lib/kinfold-api";

export function VoteForm({
  duelId,
  entries,
}: {
  duelId: string;
  entries: DuelEntry[];
}) {
  const { connected, keyPrefix, connect, disconnect } = useOwnerSession();
  const router = useRouter();
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "submitting" | "done" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleVote() {
    if (!connected || !selected) return;
    setStatus("submitting");
    setMessage("");

    try {
      const response = await ownerFetch(`/api/duels/${duelId}/vote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entry_id: selected }),
      });

      if (response.status === 204) {
        setStatus("done");
        setMessage("Vote recorded. Thanks.");
        router.refresh();
        return;
      }

      const data = await response.json().catch(() => null);
      setStatus("error");
      setMessage(data?.message ?? "Something went wrong.");
    } catch {
      setStatus("error");
      setMessage("Can't reach the backend right now.");
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <p className="mb-3 text-sm font-medium">Vote on this duel</p>
      <div className="mb-4">
        <ConnectKeyForm connectedAs={keyPrefix} onConnect={connect} onDisconnect={disconnect} />
      </div>

      {connected && status !== "done" && (
        <>
          <fieldset className="mb-4 flex flex-col gap-2">
            <legend className="sr-only">Choose which entry to vote for</legend>
            {entries.map((entry) => (
              <label
                key={entry.id}
                className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm"
              >
                <input
                  type="radio"
                  name="duel-vote"
                  value={entry.id}
                  checked={selected === entry.id}
                  onChange={() => setSelected(entry.id)}
                />
                Entry {entry.slot}
              </label>
            ))}
          </fieldset>
          <button
            type="button"
            disabled={!selected || status === "submitting"}
            onClick={handleVote}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {status === "submitting" ? "Voting..." : "Cast vote"}
          </button>
        </>
      )}

      {message && (
        <p role="status" aria-live="polite" className="mt-3 text-sm text-muted-foreground">
          {message}
        </p>
      )}
    </div>
  );
}
