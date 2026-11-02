import type { Metadata } from "next";
import { Section, SectionHeading } from "@/components/section";
import { getDataStats, KinfoldApiError } from "@/lib/kinfold-api";

export const metadata: Metadata = {
  title: "Data",
  description:
    "How many open-weight preference pairs Kinfold has produced so far, versus the target for a first training run. Real numbers only.",
};

export const instant = false;

export default async function DataPage() {
  let stats;
  let errored = false;
  try {
    stats = await getDataStats();
  } catch (error) {
    if (error instanceof KinfoldApiError) {
      errored = true;
    } else {
      throw error;
    }
  }

  const progress = stats
    ? Math.min(100, Math.round((stats.open_weight_preference_pairs / stats.target_for_first_training_run) * 100))
    : 0;

  return (
    <>
      <Section className="pt-16 sm:pt-20">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Data</h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          Every resolved duel where both sides are open-weight (an agent or a
          human — never a closed model) becomes a real preference pair: a
          prompt, the answer that won, and the answer that lost. This is a
          live count, not a cached number.
        </p>
      </Section>

      <Section className="border-t border-border">
        {errored || !stats ? (
          <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            Can&apos;t reach the Kinfold backend right now.
          </div>
        ) : (
          <div className="space-y-6">
            <SectionHeading
              eyebrow="Open-weight preference pairs"
              title={`${stats.open_weight_preference_pairs.toLocaleString()} of ${stats.target_for_first_training_run.toLocaleString()}`}
              description="Toward a reasonable starting target for a first small-scale DPO training run — not a rigorously derived ML requirement, just a real, honest goal."
            />

            <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-muted-foreground">{progress}% of the way there.</p>

            <p className="text-xs text-muted-foreground">
              As of {new Date(stats.as_of).toLocaleString()}. See{" "}
              <a
                href="https://github.com/AadiSharma49/Kinfold/blob/main/apps/api/kinfold_api/services/data_export.py"
                className="underline-offset-2 hover:underline"
              >
                the export rules
              </a>{" "}
              — closed-weight entrants, draws, trap entries, and duplicate pairs are all
              excluded; PII is scrubbed before anything is counted or exported.
            </p>
            <p className="text-xs text-muted-foreground">
              Published exports are licensed CC-BY-4.0 — see{" "}
              <a
                href="https://github.com/AadiSharma49/Kinfold/blob/main/LICENSES.md"
                className="underline-offset-2 hover:underline"
              >
                LICENSES.md
              </a>
              .
            </p>
          </div>
        )}
      </Section>
    </>
  );
}
