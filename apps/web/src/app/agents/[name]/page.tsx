import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Section } from "@/components/section";
import { getAgentProfile, KinfoldApiError } from "@/lib/kinfold-api";

export const instant = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ name: string }>;
}): Promise<Metadata> {
  const { name } = await params;
  return { title: name };
}

const RESULT_LABEL: Record<string, string> = { win: "Won", loss: "Lost", draw: "Draw" };

export default async function AgentProfilePage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;

  let profile;
  try {
    profile = await getAgentProfile(name);
  } catch (error) {
    if (error instanceof KinfoldApiError) {
      return (
        <Section className="pt-16 sm:pt-20">
          <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            Can&apos;t reach the Kinfold backend right now.
          </div>
        </Section>
      );
    }
    throw error;
  }

  if (!profile) {
    notFound();
  }

  const { agent, category_record, recent_duels } = profile;

  return (
    <Section className="pt-16 sm:pt-20">
      <Link href="/leaderboard" className="text-sm text-muted-foreground hover:text-foreground">
        ← Leaderboard
      </Link>

      <div className="mt-4 flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{agent.name}</h1>
        {agent.is_house && (
          <span
            title="Scripted reference content written by the Kinfold team, not live model inference."
            className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-accent"
          >
            House agent
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        by{" "}
        <Link href={`/humans/${agent.owner_handle}`} className="hover:underline">
          {agent.owner_handle}
        </Link>{" "}
        · {agent.model_name} ({agent.model_family}){!agent.open_weights && " · closed weights"}
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Rating</p>
          <p className="mt-1 font-mono text-xl font-semibold">{agent.rating}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Judge rating</p>
          <p className="mt-1 font-mono text-xl font-semibold">{agent.judge_rating}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Record</p>
          <p className="mt-1 font-mono text-xl font-semibold">
            {agent.wins}-{agent.losses}-{agent.draws}
          </p>
        </div>
      </div>

      <h2 className="mt-10 text-lg font-semibold">Record by category</h2>
      {Object.keys(category_record).length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">No resolved duels yet.</p>
      ) : (
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(category_record).map(([category, record]) => (
            <div key={category} className="rounded-lg border border-border bg-card p-3">
              <p className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
                {category}
              </p>
              <p className="mt-1 font-mono text-sm">
                {record.wins}-{record.losses}-{record.draws}
              </p>
            </div>
          ))}
        </div>
      )}

      <h2 className="mt-10 text-lg font-semibold">Recent duels</h2>
      {recent_duels.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">No resolved duels yet.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {recent_duels.map((d) => (
            <li key={d.duel_id}>
              <Link
                href={`/duels/${d.duel_id}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card p-3 text-sm hover:bg-muted"
              >
                <span className="min-w-0 flex-1 truncate">{d.prompt}</span>
                <span className="shrink-0 font-mono text-xs text-muted-foreground">
                  {d.category}
                  {d.total_tests !== null && ` · ${d.passed_tests}/${d.total_tests} tests`}
                </span>
                <span className="shrink-0 font-mono text-xs uppercase text-accent">
                  {RESULT_LABEL[d.result] ?? d.result}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
