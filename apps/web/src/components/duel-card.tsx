import Link from "next/link";
import type { DuelSummary } from "@/lib/kinfold-api";

const CATEGORY_LABELS: Record<string, string> = {
  code: "Code",
  debate: "Debate",
  explain: "Explain",
  hinglish: "Hinglish",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Waiting for an opponent",
  judging: "Judging",
  resolved: "Resolved",
};

export function DuelCard({ duel }: { duel: DuelSummary }) {
  return (
    <Link
      href={`/duels/${duel.id}`}
      className="block rounded-lg border border-border bg-card p-5 transition-colors hover:border-accent"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs uppercase tracking-wide text-accent">
          {CATEGORY_LABELS[duel.category] ?? duel.category}
        </span>
        <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
          {STATUS_LABELS[duel.status] ?? duel.status}
        </span>
      </div>
      <p className="mt-3 line-clamp-2 text-sm">{duel.prompt}</p>
      {duel.status === "resolved" && (
        <p className="mt-3 text-xs text-muted-foreground">
          {duel.is_draw ? "Ended in a draw" : "Winner decided"}
        </p>
      )}
    </Link>
  );
}
