import { Logo } from "@/components/logo";

export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="content-width flex flex-col gap-3 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2">
          <Logo size={14} className="text-muted-foreground" />
          Open source. License to be decided.
        </p>
        <a
          href="https://github.com/AadiSharma49/Kinfold"
          className="transition-colors hover:text-foreground"
        >
          GitHub
        </a>
      </div>
    </footer>
  );
}
