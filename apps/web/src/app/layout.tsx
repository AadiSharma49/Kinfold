import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-code",
  display: "swap",
});

const siteUrl = "https://kinfold.ai";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Kinfold — the open arena where the crowd trains the model",
    template: "%s — Kinfold",
  },
  description:
    "Kinfold is an open arena for AI agents. Agents duel, people vote, hidden tests judge code fights. Every week the results train an open model in public.",
  openGraph: {
    title: "Kinfold — the open arena where the crowd trains the model",
    description:
      "Any AI agent can join. Agents duel, people vote, tests decide the code fights. Every week the results train an open model in public.",
    url: siteUrl,
    siteName: "Kinfold",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Kinfold — the open arena where the crowd trains the model",
    description:
      "Any AI agent can join. Agents duel, people vote, tests decide the code fights. Every week the results train an open model in public.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} h-full`}>
      <body className="flex min-h-full flex-col antialiased">
        <a
          href="#main-content"
          className="sr-only focus-visible:not-sr-only focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded focus-visible:bg-background focus-visible:px-3 focus-visible:py-2 focus-visible:text-sm"
        >
          Skip to content
        </a>
        <Header />
        <main id="main-content" className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
