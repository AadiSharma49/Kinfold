const fields: Array<[string, string]> = [
  ["model", "open-mixtral-8x22b"],
  ["tokens_in", "412"],
  ["tokens_out", "187"],
  ["latency_ms", "2140"],
  ["tool_calls", "2"],
  ["autonomous", "true"],
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
