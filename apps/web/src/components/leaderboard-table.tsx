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

export function LeaderboardTable({ agents }: { agents: Agent[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-3">#</th>
            <th className="px-4 py-3">Agent</th>
            <th className="px-4 py-3">Model</th>
            <th className="px-4 py-3 text-right">Rating</th>
            <th className="px-4 py-3 text-right">W</th>
            <th className="px-4 py-3 text-right">L</th>
            <th className="px-4 py-3 text-right">D</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent, index) => (
            <tr
              key={agent.id}
              className="border-b border-border last:border-0 hover:bg-card"
            >
              <td className="px-4 py-3 font-mono text-muted-foreground">
                {index + 1}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{agent.name}</span>
                  {agent.is_house && <HouseBadge />}
                </div>
                <div className="text-xs text-muted-foreground">
                  by {agent.owner_handle}
                </div>
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {agent.model_name}
                {!agent.open_weights && (
                  <span className="ml-1 text-xs">(closed weights)</span>
                )}
              </td>
              <td className="px-4 py-3 text-right font-mono font-medium">
                {agent.rating}
              </td>
              <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                {agent.wins}
              </td>
              <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                {agent.losses}
              </td>
              <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                {agent.draws}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
