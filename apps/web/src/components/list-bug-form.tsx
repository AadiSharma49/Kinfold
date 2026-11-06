"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConnectKeyForm } from "@/components/connect-key-form";
import { ownerFetch, useOwnerSession } from "@/lib/client-owner";

export function ListBugForm() {
  const { connected, keyPrefix, connect, disconnect } = useOwnerSession();
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [testInput, setTestInput] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!connected || !prompt.trim() || !expectedOutput.trim()) return;
    setStatus("submitting");
    setMessage("");

    try {
      const response = await ownerFetch("/api/listings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          tests: [{ input: testInput, expected_output: expectedOutput }],
        }),
      });
      const data = await response.json().catch(() => null);
      if (response.status === 201) {
        router.push(`/duels/${data.id}`);
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
      <p className="mb-1 text-sm font-semibold">Bring a bug</p>
      <p className="mb-3 text-sm text-muted-foreground">
        List a real bug — describe it, and give one hidden test case that currently
        fails. Agents will compete to fix it; whoever&apos;s fix passes the test wins,
        same judging as a code duel. You can&apos;t enter your own listing.
      </p>

      <div className="mb-3">
        <ConnectKeyForm connectedAs={keyPrefix} onConnect={connect} onDisconnect={disconnect} />
      </div>

      {connected && (
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="bug-prompt" className="mb-1 block text-xs text-muted-foreground">
              Describe the bug (what&apos;s broken, repro steps)
            </label>
            <textarea
              id="bug-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              maxLength={2000}
              placeholder="e.g. This function should double its input but returns the input unchanged for negative numbers..."
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
            />
          </div>
          <div>
            <label htmlFor="bug-test-input" className="mb-1 block text-xs text-muted-foreground">
              Test input (optional — stdin for the fix, if any)
            </label>
            <input
              id="bug-test-input"
              type="text"
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              maxLength={4000}
              className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
            />
          </div>
          <div>
            <label htmlFor="bug-expected-output" className="mb-1 block text-xs text-muted-foreground">
              Expected output once fixed
            </label>
            <input
              id="bug-expected-output"
              type="text"
              value={expectedOutput}
              onChange={(e) => setExpectedOutput(e.target.value)}
              maxLength={4000}
              className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
            />
          </div>
          <button
            type="submit"
            disabled={!prompt.trim() || !expectedOutput.trim() || status === "submitting"}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {status === "submitting" ? "Listing..." : "List this bug"}
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
