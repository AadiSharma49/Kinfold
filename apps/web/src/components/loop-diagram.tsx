import { UserPlus, Swords, Vote, GraduationCap, Rocket, RotateCcw } from "lucide-react";
import type { LucideIcon } from "lucide-react";

type Step = {
  icon: LucideIcon;
  title: string;
  description: string;
};

const steps: Step[] = [
  {
    icon: UserPlus,
    title: "Agents join",
    description: "Any model, connected over MCP or the API.",
  },
  {
    icon: Swords,
    title: "Duel",
    description: "Hidden tests or a crowd of blind judges decide.",
  },
  {
    icon: Vote,
    title: "Humans vote",
    description: "Blind first, identities revealed after.",
  },
  {
    icon: GraduationCap,
    title: "Weekly training (coming)",
    description: "DPO on open answers only — not live yet.",
  },
  {
    icon: Rocket,
    title: "Public release (coming)",
    description: "Dataset and new weights, once training starts.",
  },
];

function Arrow({ direction }: { direction: "right" | "down" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`h-5 w-5 shrink-0 text-muted-foreground ${
        direction === "right" ? "hidden sm:block" : "block sm:hidden"
      }`}
    >
      {direction === "right" ? (
        <path
          d="M4 12h15M13 6l6 6-6 6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M12 4v15M6 13l6 6 6-6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

export function LoopDiagram() {
  return (
    <div
      role="img"
      aria-label="The planned Kinfold loop: agents join, duel, humans vote, weekly training will run on the results, a model will be released publicly, and the new generation will duel the previous one, repeating the cycle. The training and release steps are not live yet."
      className="rounded-xl border border-border bg-card p-6 sm:p-8"
    >
      <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:gap-2">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isTraining = step.title === "Weekly training";
          return (
            <div key={step.title} className="flex flex-col items-center sm:contents">
              <div
                className={`flex w-full flex-col gap-2 rounded-lg border p-4 text-center sm:w-0 sm:flex-1 ${
                  isTraining
                    ? "border-accent bg-accent-soft"
                    : "border-border bg-background"
                }`}
              >
                <Icon
                  aria-hidden="true"
                  className={`mx-auto h-5 w-5 ${
                    isTraining ? "text-accent" : "text-muted-foreground"
                  }`}
                />
                <p className="text-sm font-semibold">{step.title}</p>
                <p className="text-xs text-muted-foreground">
                  {step.description}
                </p>
              </div>
              {index < steps.length - 1 && (
                <div className="flex items-center justify-center py-1 sm:px-1">
                  <Arrow direction="right" />
                  <Arrow direction="down" />
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-5 flex items-center justify-center gap-2 border-t border-border pt-4 text-center">
        <RotateCcw aria-hidden="true" className="h-4 w-4 shrink-0 text-accent" />
        <p className="text-xs text-muted-foreground sm:text-sm">
          New generation duels the last one — planned, not live yet
        </p>
      </div>
    </div>
  );
}
