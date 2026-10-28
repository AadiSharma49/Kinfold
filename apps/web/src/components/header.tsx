import Link from "next/link";
import { Wordmark } from "@/components/logo";

const navLinks = [
  { href: "/duels", label: "Duels" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/roadmap", label: "Roadmap" },
  { href: "https://github.com/AadiSharma49/Kinfold", label: "GitHub" },
];

export function Header() {
  return (
    <header className="border-b border-border">
      <div className="content-width flex h-16 items-center justify-between">
        <Link href="/">
          <Wordmark />
        </Link>
        <nav aria-label="Primary" className="flex items-center gap-6">
          <ul className="hidden items-center gap-6 sm:flex">
            {navLinks.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          <Link
            href="#waitlist"
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
          >
            Join waitlist
          </Link>
        </nav>
      </div>
    </header>
  );
}
