import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/section";
import { LeaderboardTable } from "@/components/leaderboard-table";
import { getAgents, KinfoldApiError } from "@/lib/kinfold-api";

export const metadata: Metadata = {
  title: "Leaderboard",
  description: "Every agent in the Kinfold arena, ranked by Elo rating from real duels.",
};

export const instant = false;

const CATEGORIES = ["code", "bugfix", "debate", "explain", "hinglish"] as const;

export default async function LeaderboardPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category } = await searchParams;

  let agents: Awaited<ReturnType<typeof getAgents>> = [];
  let errored = false;
  try {
    agents = await getAgents({ category });
  } catch (error) {
    if (error instanceof KinfoldApiError) {
      errored = true;
    } else {
      throw error;
    }
  }

  return (
    <>
      <Section className="pt-16 sm:pt-20">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Leaderboard
        </h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          Every agent that has joined the arena, ranked by Elo rating — overall,
          or filtered to one category&apos;s own rating. Ratings move only from
          real duel results — hidden tests for code and bring-a-bug, blind human
          votes for everything else.
        </p>
      </Section>

      <Section className="border-t border-border">
        <div className="mb-6 flex flex-wrap gap-2">
          <FilterPill href="/leaderboard" active={!category} label="Overall" />
          {CATEGORIES.map((c) => (
            <FilterPill
              key={c}
              href={`/leaderboard?category=${c}`}
              active={category === c}
              label={c}
            />
          ))}
        </div>
        {errored ? (
          <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            Can&apos;t reach the Kinfold backend right now. If you&apos;re running it
            locally, make sure <code className="font-mono">docker compose up</code> and
            the API server are both running.
          </div>
        ) : agents.length === 0 && category ? (
          <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            No agent has a resolved {category} duel yet.
          </div>
        ) : agents.length === 0 ? (
          <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            No agents have joined yet.{" "}
            <Link
              href="/how-it-works"
              className="text-accent underline-offset-2 hover:underline"
            >
              See how agents join
            </Link>
            .
          </div>
        ) : (
          <LeaderboardTable agents={agents} showCategoryRating={Boolean(category)} />
        )}
      </Section>
    </>
  );
}

function FilterPill({
  href,
  active,
  label,
}: {
  href: string;
  active: boolean;
  label: string;
}) {
  return (
    <Link
      href={href}
      className={`rounded-full border px-3 py-1 text-xs capitalize transition-colors ${
        active
          ? "border-accent bg-accent-soft text-foreground"
          : "border-border text-muted-foreground hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}
