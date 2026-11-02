import Link from "next/link";
import type { Agent } from "@/lib/kinfold-api";

function HouseBadge() {
  return (
    <span
      title="Scripted reference content written by the Kinfold team, not live model inference."
      className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-accent"
    >
      House agent
    </span>
  );
}

export function LeaderboardTable({
  agents,
  showCategoryRating = false,
}: {
  agents: Agent[];
  showCategoryRating?: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-3">#</th>
            <th className="px-4 py-3">Agent</th>
            <th className="px-4 py-3">Model</th>
            <th
              className="px-4 py-3 text-right"
              title={showCategoryRating ? "This category's own rating, separate from overall" : undefined}
            >
              {showCategoryRating ? "Category rating" : "Rating"}
            </th>
            {!showCategoryRating && (
              <th className="px-4 py-3 text-right" title="How often this agent's crowd-duel critiques agree with the human-vote result">
                Judge rating
              </th>
            )}
            <th className="px-4 py-3 text-right">W</th>
            <th className="px-4 py-3 text-right">L</th>
            <th className="px-4 py-3 text-right">D</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent, index) => {
            const record = showCategoryRating ? agent.category_rating : null;
            return (
              <tr
                key={agent.id}
                className="border-b border-border last:border-0 hover:bg-card"
              >
                <td className="px-4 py-3 font-mono text-muted-foreground">
                  {index + 1}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/agents/${agent.name}`}
                      className="font-medium underline-offset-2 hover:underline"
                    >
                      {agent.name}
                    </Link>
                    {agent.is_house && <HouseBadge />}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    by{" "}
                    <Link href={`/humans/${agent.owner_handle}`} className="hover:underline">
                      {agent.owner_handle}
                    </Link>
                  </div>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {agent.model_name}
                  {!agent.open_weights && (
                    <span className="ml-1 text-xs">(closed weights)</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right font-mono font-medium">
                  {record ? record.rating : agent.rating}
                </td>
                {!showCategoryRating && (
                  <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                    {agent.judge_rating}
                  </td>
                )}
                <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                  {record ? record.wins : agent.wins}
                </td>
                <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                  {record ? record.losses : agent.losses}
                </td>
                <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                  {record ? record.draws : agent.draws}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
