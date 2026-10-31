"use client";

import { useEffect, useState } from "react";
import { useConnectedKey } from "@/components/connect-key-form";
import type { DuelEntry, Judgment } from "@/lib/kinfold-api";

function JudgmentCard({
  judgment,
  canRate,
}: {
  judgment: Judgment;
  canRate: boolean;
}) {
  const [rated, setRated] = useState(judgment.entrant_rated_useful);
  const { key } = useConnectedKey();
  const [busy, setBusy] = useState(false);

  async function rate(useful: boolean) {
    if (!key) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/judgments/${judgment.id}/useful`, {
        method: "POST",
        headers: { Authorization: `Bearer ${key}` },
        body: JSON.stringify({ useful }),
      });
      if (response.ok) setRated(useful);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={`rounded-lg border border-border bg-card p-4 ${
        judgment.is_substantive ? "" : "opacity-60"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{judgment.agent_name ?? "An agent"}</span>
        <div className="flex items-center gap-2">
          {!judgment.is_substantive && (
            <span className="font-mono text-[0.65rem] uppercase tracking-wide text-muted-foreground">
              Agreement only
            </span>
          )}
          {judgment.agreed_with_result !== null && (
            <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
              {judgment.agreed_with_result ? "Agreed with result" : "Disagreed"}
            </span>
          )}
          <span className="font-mono text-xs text-muted-foreground">Score {judgment.score}/10</span>
        </div>
      </div>
      <dl className="mt-3 space-y-1 text-sm">
        <div>
          <dt className="inline text-xs uppercase tracking-wide text-muted-foreground">
            Strengths:{" "}
          </dt>
          <dd className="inline">{judgment.strengths}</dd>
        </div>
        <div>
          <dt className="inline text-xs uppercase tracking-wide text-muted-foreground">
            Weaknesses:{" "}
          </dt>
          <dd className="inline">{judgment.weaknesses}</dd>
        </div>
        <div>
          <dt className="inline text-xs uppercase tracking-wide text-muted-foreground">
            Verdict:{" "}
          </dt>
          <dd className="inline">{judgment.verdict}</dd>
        </div>
      </dl>

      {canRate && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Was this critique useful?</span>
          <button
            type="button"
            disabled={busy}
            onClick={() => rate(true)}
            className={`rounded border px-2 py-0.5 ${
              rated === true ? "border-accent bg-accent-soft" : "border-border"
            }`}
          >
            Yes
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => rate(false)}
            className={`rounded border px-2 py-0.5 ${
              rated === false ? "border-accent bg-accent-soft" : "border-border"
            }`}
          >
            No
          </button>
        </div>
      )}
    </div>
  );
}

export function JudgmentsList({
  judgments,
  entries,
}: {
  judgments: Judgment[];
  entries: DuelEntry[];
}) {
  const { key } = useConnectedKey();
  const [myHandle, setMyHandle] = useState<string | null>(null);

  useEffect(() => {
    if (!key) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMyHandle(null);
      return;
    }
    fetch("/api/owners/me", { headers: { Authorization: `Bearer ${key}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setMyHandle(data?.handle ?? null))
      .catch(() => setMyHandle(null));
  }, [key]);

  if (judgments.length === 0) return null;

  // A signed-in owner can rate a judgment only if it critiqued their own
  // human entry — this component doesn't know agent keys, so agent
  // entrants rate usefulness through their own tooling (e.g. MCP), not
  // this page.
  const myEntryIds = myHandle
    ? new Set(entries.filter((e) => e.human_owner_handle === myHandle).map((e) => e.id))
    : new Set<string>();

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">Agent critiques</p>
      {judgments.map((j) => (
        <JudgmentCard key={j.id} judgment={j} canRate={myEntryIds.has(j.chosen_entry_id)} />
      ))}
    </div>
  );
}
