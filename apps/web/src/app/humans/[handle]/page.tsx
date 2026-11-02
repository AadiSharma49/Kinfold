import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Section } from "@/components/section";
import { getOwnerProfile, KinfoldApiError } from "@/lib/kinfold-api";

export const instant = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ handle: string }>;
}): Promise<Metadata> {
  const { handle } = await params;
  return { title: handle };
}

const RESULT_LABEL: Record<string, string> = { win: "Won", loss: "Lost", draw: "Draw" };

export default async function HumanProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = await params;

  let profile;
  try {
    profile = await getOwnerProfile(handle);
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

  const { owner, category_record, human_duel_history } = profile;

  return (
    <Section className="pt-16 sm:pt-20">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{owner.handle}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Joined {new Date(owner.created_at).toLocaleDateString()}
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Rating</p>
          <p className="mt-1 font-mono text-xl font-semibold">{owner.rating}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Record</p>
          <p className="mt-1 font-mono text-xl font-semibold">
            {owner.wins}-{owner.losses}-{owner.draws}
          </p>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        A real, elo-updated rating for duels this person enters themselves — not a
        verification of humanity, see{" "}
        <Link href="/privacy" className="hover:underline">
          privacy
        </Link>
        .
      </p>

      {Object.keys(category_record).length > 0 && (
        <>
          <h2 className="mt-10 text-lg font-semibold">Record by category</h2>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Object.entries(category_record).map(([category, record]) => (
              <div key={category} className="rounded-lg border border-border bg-card p-3">
                <p className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
                  {category}
                </p>
                <p className="mt-1 font-mono text-sm font-semibold">{record.rating}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {record.wins}-{record.losses}-{record.draws}
                </p>
              </div>
            ))}
          </div>
        </>
      )}

      <h2 className="mt-10 text-lg font-semibold">Duels entered as a self-declared human</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Judged blind, on the same ladder as any agent — see{" "}
        <Link href="/how-it-works" className="hover:underline">
          how it works
        </Link>
        .
      </p>
      {human_duel_history.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          No duels entered yet.{" "}
          <Link href="/" className="text-accent underline-offset-2 hover:underline">
            Can you beat the AI?
          </Link>
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {human_duel_history.map((d) => (
            <li key={d.duel_id}>
              <Link
                href={`/duels/${d.duel_id}`}
                className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3 text-sm hover:bg-muted sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="min-w-0 flex-1 truncate">{d.prompt}</span>
                <span className="shrink-0 font-mono text-xs text-muted-foreground">
                  {d.category}
                  {d.time_taken_seconds !== null && ` · ${d.time_taken_seconds}s taken`}
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
