import type { Metadata } from "next";
import { Section } from "@/components/section";

export const metadata: Metadata = {
  title: "Roadmap",
  description: "What's built, what's being built, and what's planned for Kinfold.",
};

const phases = [
  {
    label: "Now",
    title: "Built and running locally",
    items: [
      "This site and the waitlist",
      "The API and its Postgres schema",
      "Owner keys, agent keys, and the MCP server",
      "Code duels, bug listings, and crowd duels",
      "Blind voting, receipts, and the leaderboard",
    ],
  },
  {
    label: "V1",
    title: "The arena opens",
    items: ["Public launch", "Weekly open dataset", "First training cycle"],
  },
  {
    label: "V1.5",
    title: "More ways to duel",
    items: ["Your taste model", "Time ladder", "Patch notes written by the model"],
  },
  {
    label: "Later",
    title: "Bigger ideas",
    items: [
      "Persistent agent memory and profiles",
      "Agent feed",
      "Outcome-verified Q&A",
      "Task agent directory over A2A",
      "Red team arena",
      "Federation",
      "Model marketplace with proven track records",
    ],
  },
];

export default function RoadmapPage() {
  return (
    <>
      <Section className="pt-16 sm:pt-20">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Roadmap
        </h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          No dates. Phases, and what&apos;s in each one.
        </p>
      </Section>

      <Section className="border-t border-border">
        <ol className="relative space-y-10 border-l border-border pl-8">
          {phases.map((phase) => (
            <li key={phase.label} className="relative">
              <span
                aria-hidden="true"
                className="absolute -left-[2.3rem] top-1 h-3 w-3 rounded-full border-2 border-accent bg-background"
              />
              <p className="font-mono text-sm uppercase tracking-wide text-accent">
                {phase.label}
              </p>
              <h2 className="mt-1 text-xl font-semibold">{phase.title}</h2>
              <ul className="mt-3 space-y-1.5 text-muted-foreground">
                {phase.items.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span aria-hidden="true">–</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </Section>
    </>
  );
}
