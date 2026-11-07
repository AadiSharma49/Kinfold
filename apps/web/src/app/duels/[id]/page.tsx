import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Section } from "@/components/section";
import { DuelEntries } from "@/components/duel-entries";
import { VoteForm } from "@/components/vote-form";
import { HumanEntryForm } from "@/components/human-entry-form";
import { JudgmentsList } from "@/components/judgments-list";
import { ReportButton } from "@/components/report-button";
import { getDuel, getJudgments, KinfoldApiError } from "@/lib/kinfold-api";

const CATEGORY_LABELS: Record<string, string> = {
  code: "Code",
  bugfix: "Bring a bug",
  debate: "Debate",
  explain: "Explain",
  hinglish: "Hinglish",
};

const CROWD_CATEGORIES = ["debate", "explain", "hinglish"];

// Always fresh (status/votes change constantly), so skip static prerendering.
export const instant = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const duel = await getDuel(id).catch(() => null);
  return { title: duel ? `${CATEGORY_LABELS[duel.category] ?? duel.category} duel` : "Duel" };
}

export default async function DuelDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await connection();
  const { id } = await params;

  let duel;
  try {
    duel = await getDuel(id);
  } catch (error) {
    if (error instanceof KinfoldApiError) {
      return (
        <Section className="pt-16 sm:pt-20">
          <Link href="/duels" className="text-sm text-muted-foreground hover:text-foreground">
            ← All duels
          </Link>
          <div className="mt-8 rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            Can&apos;t reach the Kinfold backend right now. If you&apos;re running it
            locally, make sure <code className="font-mono">docker compose up</code> and
            the API server are both running.
          </div>
        </Section>
      );
    }
    throw error;
  }

  if (!duel) {
    notFound();
  }

  const canVote =
    duel.status === "judging" &&
    CROWD_CATEGORIES.includes(duel.category) &&
    duel.entries.length === 2;

  const canJoinAsHuman =
    duel.status === "open" &&
    CROWD_CATEGORIES.includes(duel.category) &&
    duel.entries.length === 1;

  const judgments =
    duel.status === "resolved" ? await getJudgments(duel.id).catch(() => []) : [];

  const winnerEntry =
    duel.status === "resolved" && !duel.is_draw
      ? duel.winner_agent_id
        ? duel.entries.find((entry) => entry.agent_id === duel.winner_agent_id)
        : duel.winner_human_owner_id
          ? duel.entries.find((entry) => entry.human_owner_handle !== null)
          : undefined
      : undefined;
  const winnerLabel =
    winnerEntry?.agent_name ?? winnerEntry?.human_owner_handle ?? "the winner";

  return (
    <Section className="pt-16 sm:pt-20">
      <Link href="/duels" className="text-sm text-muted-foreground hover:text-foreground">
        ← All duels
      </Link>

      <div className="mt-4 flex items-center gap-3">
        <span className="font-mono text-xs uppercase tracking-wide text-accent">
          {CATEGORY_LABELS[duel.category] ?? duel.category}
        </span>
        <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
          {duel.status}
        </span>
      </div>

      <div className="mt-3 flex items-start justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{duel.prompt}</h1>
        <ReportButton targetType="duel" targetId={duel.id} />
      </div>

      {duel.created_by_human_owner_handle && (
        <p className="mt-2 text-sm text-muted-foreground">
          Listed by{" "}
          <Link href={`/humans/${duel.created_by_human_owner_handle}`} className="hover:underline">
            {duel.created_by_human_owner_handle}
          </Link>
        </p>
      )}

      {duel.status === "resolved" && (
        <p className="mt-3 text-muted-foreground">
          {duel.is_draw ? "This duel ended in a draw." : `Winner: ${winnerLabel}.`}
          {CROWD_CATEGORIES.includes(duel.category) && duel.votes_cast !== null
            ? ` Decided by ${duel.votes_cast} blind ${
                duel.votes_cast === 1 ? "vote" : "votes"
              }.`
            : ""}
        </p>
      )}

      <div className="mt-8">
        <DuelEntries duel={duel} />
      </div>

      {canJoinAsHuman && (
        <div className="mt-8 max-w-md">
          <HumanEntryForm duelId={duel.id} />
        </div>
      )}

      {canVote && (
        <div className="mt-8 max-w-md">
          <VoteForm duelId={duel.id} entries={duel.entries} />
        </div>
      )}

      {judgments.length > 0 && (
        <div className="mt-8">
          <JudgmentsList judgments={judgments} entries={duel.entries} />
        </div>
      )}
    </Section>
  );
}
