"use client";

import { useState } from "react";
import type { ApiKeyCreated } from "@/lib/kinfold-api";

export function CreateAgentForm({
  ownerKey,
  onCreated,
}: {
  ownerKey: string;
  onCreated: (key: ApiKeyCreated) => void;
}) {
  const [name, setName] = useState("");
  const [modelName, setModelName] = useState("");
  const [modelFamily, setModelFamily] = useState("");
  const [openWeights, setOpenWeights] = useState(true);
  const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("submitting");
    setMessage("");

    try {
      const response = await fetch("/api/agents", {
        method: "POST",
        headers: { Authorization: `Bearer ${ownerKey}` },
        body: JSON.stringify({
          name,
          model_name: modelName,
          model_family: modelFamily,
          open_weights: openWeights,
        }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        setStatus("error");
        setMessage(data?.detail ?? "Couldn't create the agent. Check the name and try again.");
        return;
      }
      onCreated(data.key);
      setName("");
      setModelName("");
      setModelFamily("");
      setStatus("idle");
    } catch {
      setStatus("error");
      setMessage("Can't reach the Kinfold backend right now.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border border-border bg-card p-5">
      <p className="text-sm font-medium">Create an agent</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="my-agent"
            required
            minLength={3}
            maxLength={40}
            pattern="[a-z0-9_-]{3,40}"
            title="lowercase letters, numbers, - and _ only"
            className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Model name
          <input
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="e.g. llama-3.1-70b"
            required
            className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Model family
          <input
            value={modelFamily}
            onChange={(e) => setModelFamily(e.target.value)}
            placeholder="e.g. llama"
            required
            className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          />
        </label>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={openWeights}
            onChange={(e) => setOpenWeights(e.target.checked)}
          />
          Open weights
        </label>
      </div>
      <button
        type="submit"
        disabled={status === "submitting"}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {status === "submitting" ? "Creating..." : "Create agent"}
      </button>
      {message && (
        <p role="status" aria-live="polite" className="text-sm text-accent">
          {message}
        </p>
      )}
    </form>
  );
}
