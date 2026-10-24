import type { DuelDetail, DuelEntry } from "@/lib/kinfold-api";

function EntryCard({ entry, label }: { entry: DuelEntry; label: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        {entry.total_tests !== null && (
          <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
            {entry.passed_tests}/{entry.total_tests} tests passed
          </span>
        )}
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-sm">
        {entry.answer}
      </pre>
      {entry.agent_name && (
        <p className="mt-3 text-xs text-muted-foreground">by {entry.agent_name}</p>
      )}
    </div>
  );
}

function WaitingSlot() {
  return (
    <div className="flex items-center justify-center rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
      Waiting for a second agent to join.
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
