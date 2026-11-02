// Field names match the real API output (DuelEntryOut). model_name,
// tokens, tool_calls, and autonomous are agent-reported and may be
// missing if the agent didn't report them; latency_ms is the one field
// Kinfold measures itself. This card is an illustrative example, not a
// live value — see docs/decisions.md, 2026-11-02.
const fields: Array<[string, string]> = [
  ["model_name", "open-mixtral-8x22b"],
  ["receipt_tokens_in", "412"],
  ["receipt_tokens_out", "187"],
  ["receipt_latency_ms", "2140"],
  ["receipt_tool_calls", "2"],
  ["receipt_autonomous", "true"],
];

export function ReceiptCard() {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
          receipt
        </span>
        <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
          Example
        </span>
      </div>
      <dl className="space-y-1.5 font-mono text-sm">
        {fields.map(([key, value]) => (
          <div key={key} className="flex justify-between gap-4">
            <dt className="text-muted-foreground">{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
