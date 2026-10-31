"use client";

import { useState } from "react";
import { useConnectedKey } from "@/components/connect-key-form";

export function ReportButton({
  targetType,
  targetId,
}: {
  targetType: "duel" | "entry" | "judgment";
  targetId: string;
}) {
  const { key } = useConnectedKey();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "done" | "error">("idle");

  if (!key) return null;

  if (status === "done") {
    return <span className="text-xs text-muted-foreground">Reported. Thanks.</span>;
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-muted-foreground underline-offset-2 hover:underline"
      >
        Report
      </button>
    );
  }

  async function submit() {
    if (!reason.trim()) return;
    setStatus("submitting");
    try {
      const response = await fetch("/api/reports", {
        method: "POST",
        headers: { Authorization: `Bearer ${key}` },
        body: JSON.stringify({ target_type: targetType, target_id: targetId, reason }),
      });
      setStatus(response.ok ? "done" : "error");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      <input
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Why are you reporting this?"
        maxLength={500}
        className="w-48 rounded border border-border bg-background px-2 py-1 text-foreground outline-none focus-visible:outline-2"
      />
      <button
        type="button"
        onClick={submit}
        disabled={!reason.trim() || status === "submitting"}
        className="rounded border border-border px-2 py-1 disabled:opacity-60"
      >
        {status === "submitting" ? "Sending..." : "Send"}
      </button>
      {status === "error" && <span className="text-accent">Couldn&apos;t send.</span>}
    </div>
  );
}
