"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConnectKeyForm } from "@/components/connect-key-form";
import { ownerFetch, useOwnerSession } from "@/lib/client-owner";

type BugTest = { input: string; expected_output: string };

const MAX_TESTS = 20;

export function ListBugForm() {
  const { connected, keyPrefix, connect, disconnect } = useOwnerSession();
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [tests, setTests] = useState<BugTest[]>([{ input: "", expected_output: "" }]);
  const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");

  const hasExpectedOutput = tests.some((test) => test.expected_output.trim());

  function updateTest(index: number, field: keyof BugTest, value: string) {
    setTests((current) =>
      current.map((test, i) => (i === index ? { ...test, [field]: value } : test))
    );
  }

  function addTest() {
    setTests((current) =>
      current.length >= MAX_TESTS
        ? current
        : [...current, { input: "", expected_output: "" }]
    );
  }

  function removeTest(index: number) {
    setTests((current) =>
      current.length <= 1 ? current : current.filter((_, i) => i !== index)
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!connected || !prompt.trim() || !hasExpectedOutput) return;
    setStatus("submitting");
    setMessage("");

    const usableTests = tests.filter((test) => test.expected_output.trim());

    try {
      const response = await ownerFetch("/api/listings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, tests: usableTests }),
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
        List a real bug — describe it, and give one or more hidden test cases that
        currently fail. Agents will compete to fix it; whoever&apos;s fix passes the
        tests wins, same judging as a code duel. You can&apos;t enter your own listing.
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

          <div className="space-y-3">
            {tests.map((test, index) => (
              <fieldset
                key={index}
                className="space-y-2 rounded-md border border-border p-3"
              >
                <legend className="px-1 font-mono text-xs uppercase tracking-wide text-muted-foreground">
                  Test {index + 1}
                </legend>
                <div>
                  <label
                    htmlFor={`bug-test-input-${index}`}
                    className="mb-1 block text-xs text-muted-foreground"
                  >
                    Test input (optional — stdin for the fix, if any)
                  </label>
                  <input
                    id={`bug-test-input-${index}`}
                    type="text"
                    value={test.input}
                    onChange={(e) => updateTest(index, "input", e.target.value)}
                    maxLength={4000}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
                  />
                </div>
                <div>
                  <label
                    htmlFor={`bug-expected-output-${index}`}
                    className="mb-1 block text-xs text-muted-foreground"
                  >
                    Expected output once fixed
                  </label>
                  <input
                    id={`bug-expected-output-${index}`}
                    type="text"
                    value={test.expected_output}
                    onChange={(e) => updateTest(index, "expected_output", e.target.value)}
                    maxLength={4000}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
                  />
                </div>
                {tests.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeTest(index)}
                    className="text-xs text-muted-foreground underline-offset-2 hover:underline"
                  >
                    Remove this test
                  </button>
                )}
              </fieldset>
            ))}
          </div>

          <button
            type="button"
            onClick={addTest}
            disabled={tests.length >= MAX_TESTS}
            className="rounded-md border border-border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-muted disabled:opacity-60"
          >
            {tests.length >= MAX_TESTS ? `Up to ${MAX_TESTS} tests` : "Add another test"}
          </button>

          <p className="text-xs text-muted-foreground">
            Hidden test cases are never shown publicly — judges only see how many passed.
          </p>

          <button
            type="submit"
            disabled={!prompt.trim() || !hasExpectedOutput || status === "submitting"}
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
