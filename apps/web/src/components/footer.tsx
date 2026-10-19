export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="content-width flex flex-col gap-3 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p>Open source. License to be decided.</p>
        <a
          href="https://github.com"
          className="transition-colors hover:text-foreground"
        >
          GitHub
        </a>
      </div>
    </footer>
  );
}
