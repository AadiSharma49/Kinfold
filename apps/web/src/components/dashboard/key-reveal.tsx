"use client";

import { useState } from "react";

export function KeyReveal({ label, rawKey }: { label: string; rawKey: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(rawKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API can be unavailable (permissions, non-secure context) —
      // the key is still selectable text, so this isn't fatal.
    }
  }

  return (
    <div className="rounded-lg border border-accent bg-accent-soft p-4">
      <p className="text-sm font-medium">{label}</p>
      <div className="mt-2 flex items-center gap-2">
        <code className="flex-1 overflow-x-auto rounded bg-background px-3 py-2 font-mono text-sm">
          {rawKey}
        </code>
        <button
          type="button"
          onClick={handleCopy}
          className="shrink-0 rounded-md border border-border px-3 py-2 text-xs font-medium transition-colors hover:bg-muted"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        This is the only time the full key is shown. Store it now — it cannot be shown again.
      </p>
    </div>
  );
}
