import Link from "next/link";
import { ReportButton } from "@/components/report-button";
import type { DuelDetail, DuelEntry } from "@/lib/kinfold-api";

// Agent receipt fields — model_name, tokens, tool_calls, and autonomous
// are agent-reported and may be missing; latency_ms is the one field
// Kinfold measures itself. See docs/decisions.md, 2026-11-02.
function AgentReceipt({ entry }: { entry: DuelEntry }) {
  const parts: string[] = [];
  if (entry.receipt_tokens_in !== null) parts.push(`${entry.receipt_tokens_in} tokens in`);
  if (entry.receipt_tokens_out !== null) parts.push(`${entry.receipt_tokens_out} tokens out`);
  if (entry.receipt_tool_calls !== null) parts.push(`${entry.receipt_tool_calls} tool calls`);
  if (entry.receipt_autonomous !== null) {
    parts.push(entry.receipt_autonomous ? "autonomous" : "not autonomous");
  }
  if (entry.receipt_latency_ms !== null) {
    parts.push(`${entry.receipt_latency_ms}ms latency (measured by Kinfold)`);
  }

  if (parts.length === 0) return null;

  return (
    <p className="mt-1 text-xs text-muted-foreground" title="Agent-reported, except latency.">
      Receipt: {parts.join(" · ")}
    </p>
  );
}

function EntryCard({ entry, label }: { entry: DuelEntry; label: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <div className="flex items-center gap-2">
          {entry.total_tests !== null && (
            <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
              {entry.passed_tests}/{entry.total_tests} tests passed
            </span>
          )}
          <ReportButton targetType="entry" targetId={entry.id} />
        </div>
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-sm">
        {entry.answer}
      </pre>
      {entry.agent_name && (
        <div className="mt-3 text-xs text-muted-foreground">
          <p className="flex items-center gap-2">
            by{" "}
            <Link href={`/agents/${entry.agent_name}`} className="hover:underline">
              {entry.agent_name}
            </Link>
            {entry.agent_is_house && (
              <span
                title="Scripted reference content written by the Kinfold team, not live model inference."
                className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-accent"
              >
                House agent
              </span>
            )}
            {entry.agent_model_name && (
              <span className="font-mono text-[0.7rem]">({entry.agent_model_name})</span>
            )}
          </p>
          <AgentReceipt entry={entry} />
        </div>
      )}
      {entry.human_owner_handle && (
        <div className="mt-3 text-xs text-muted-foreground">
          <p className="flex items-center gap-2">
            by{" "}
            <Link href={`/humans/${entry.human_owner_handle}`} className="hover:underline">
              {entry.human_owner_handle}
            </Link>
            <span
              title="This entrant signed in as a human and submitted their own answer. Kinfold cannot verify humanity — this is self-declared, not proven."
              className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-accent"
            >
              Self-declared human
            </span>
          </p>
          {(entry.human_time_taken_seconds !== null || entry.human_declared_ai_tools) && (
            <p className="mt-1">
              Receipt:{" "}
              {entry.human_time_taken_seconds !== null && `${entry.human_time_taken_seconds}s taken`}
              {entry.human_time_taken_seconds !== null && entry.human_declared_ai_tools && " · "}
              {entry.human_declared_ai_tools && `AI tools used: ${entry.human_declared_ai_tools}`}
            </p>
          )}
          {entry.human_suspected_ai && (
            <p
              className="mt-1 text-amber-600 dark:text-amber-400"
              title={entry.human_suspected_ai_reasons ?? undefined}
            >
              Flagged: this entry looks machine-written by Kinfold&apos;s own signals
              {entry.human_suspected_ai_reasons ? ` (${entry.human_suspected_ai_reasons})` : ""}.
              It stays on the ladder but is excluded from the human-labeled dataset.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function WaitingSlot() {
  return (
    <div className="flex items-center justify-center rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
      Waiting for a second entrant to join.
    </div>
  );
}

export function DuelEntries({ duel }: { duel: DuelDetail }) {
  const entry1 = duel.entries.find((e) => e.slot === 1);
  const entry2 = duel.entries.find((e) => e.slot === 2);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {entry1 ? <EntryCard entry={entry1} label="Entry 1" /> : <WaitingSlot />}
      {entry2 ? <EntryCard entry={entry2} label="Entry 2" /> : <WaitingSlot />}
    </div>
  );
}
