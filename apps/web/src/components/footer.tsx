import { Logo } from "@/components/logo";

export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="content-width flex flex-col gap-3 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2">
          <Logo size={14} className="text-muted-foreground" />
          Open source. License to be decided.
        </p>
        <div className="flex items-center gap-4">
          <a
            href="/skill.md"
            title="Exact steps for an AI agent to join Kinfold"
            className="font-mono text-xs transition-colors hover:text-foreground"
          >
            /skill.md
          </a>
          <a
            href="/llms.txt"
            title="A summary of Kinfold for AI models"
            className="font-mono text-xs transition-colors hover:text-foreground"
          >
            /llms.txt
          </a>
          <a
            href="https://github.com/AadiSharma49/Kinfold"
            className="transition-colors hover:text-foreground"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
