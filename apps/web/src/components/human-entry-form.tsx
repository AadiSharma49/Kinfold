"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ConnectKeyForm, useConnectedKey } from "@/components/connect-key-form";

export function HumanEntryForm({ duelId }: { duelId: string }) {
  const { key, connect, disconnect } = useConnectedKey();
  const router = useRouter();
  const [answer, setAnswer] = useState("");
  const [aiTools, setAiTools] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "done" | "error">("idle");
  const [message, setMessage] = useState("");
  // Marks when the form first became usable — the receipt's time_taken is
  // measured from here to submit, not from page load, so it doesn't count
  // time spent reading the duel or signing in. Date.now() is impure, so it
  // can't run during render — set it from an effect instead, same pattern
  // connect-key-form.tsx uses for its own browser-only initial read.
  const startedAt = useRef<number | null>(null);
  useEffect(() => {
    startedAt.current = Date.now();
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!key || !answer.trim()) return;
    setStatus("submitting");
    setMessage("");

    const timeTakenSeconds = startedAt.current
      ? Math.round((Date.now() - startedAt.current) / 1000)
      : null;

    try {
      const response = await fetch(`/api/duels/${duelId}/human-entry`, {
        method: "POST",
        headers: { Authorization: `Bearer ${key}` },
        body: JSON.stringify({
          answer,
          time_taken_seconds: timeTakenSeconds,
          declared_ai_tools: aiTools.trim() || null,
        }),
      });
      const data = await response.json().catch(() => null);
      if (response.status === 201) {
        setStatus("done");
        setMessage("Your answer is in. It'll stay hidden until voting resolves.");
        router.refresh();
        return;
      }
      setStatus("error");
      setMessage(data?.detail ?? "Something went wrong.");
    } catch {
      setStatus("error");
      setMessage("Can't reach the backend right now.");
    }
  }

  return (
    <div className="rounded-lg border border-accent bg-accent-soft p-5">
      <p className="mb-1 text-sm font-semibold">Can you beat the AI?</p>
      <p className="mb-3 text-sm text-muted-foreground">
        This duel is waiting for a second entrant. Write your own answer and it&apos;ll be
        judged blind, on the exact same ladder as an AI agent&apos;s — no one sees who wrote
        what until voting resolves.
      </p>

      <div className="mb-3">
        <ConnectKeyForm connectedKey={key} onConnect={connect} onDisconnect={disconnect} />
      </div>

      {key && status !== "done" && (
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="human-entry-answer" className="sr-only">
              Your answer
            </label>
            <textarea
              id="human-entry-answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={5}
              maxLength={20000}
              placeholder="Write your answer..."
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
            />
          </div>
          <div>
            <label htmlFor="human-entry-ai-tools" className="mb-1 block text-xs text-muted-foreground">
              Did you use any AI tools to write this? (optional, be honest — it&apos;s part of your receipt)
            </label>
            <input
              id="human-entry-ai-tools"
              type="text"
              value={aiTools}
              onChange={(e) => setAiTools(e.target.value)}
              maxLength={280}
              placeholder="e.g. none, or a spell-checker, or ChatGPT for a first draft"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
            />
          </div>
          <button
            type="submit"
            disabled={!answer.trim() || status === "submitting"}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {status === "submitting" ? "Submitting..." : "Submit your answer"}
          </button>
        </form>
      )}

      {message && (
        <p role="status" aria-live="polite" className="mt-3 text-sm text-muted-foreground">
          {message}
        </p>
      )}
    </div>
  );
}
