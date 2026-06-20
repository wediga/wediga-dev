import Link from "next/link";
import { INTRO } from "@/components/hero/content";

// The quiet shell for the non-landing public pages (login, impressum,
// link-invalid). It carries the dark Landing surface so these pages read as
// the same site, but stays still and typographic: no hero, no WebGL, no ride.
// Route groups do not change the URL, so /login, /impressum and /link-invalid
// keep their paths; only their presentation moves into this common shell.
export default function QuietLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between px-6 py-6">
        <Link
          href="/"
          className="rounded-sm text-sm font-medium tracking-[-0.02em] text-ink transition-colors hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
        >
          {INTRO.name}
        </Link>
        <Link
          href="/"
          className="rounded-sm text-sm text-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
        >
          Zur Startseite
        </Link>
      </header>

      <main className="flex flex-1 flex-col items-center justify-start px-6 pb-24 pt-[clamp(3rem,16vh,10rem)]">
        {children}
      </main>

      <footer className="mx-auto flex w-full max-w-3xl items-center justify-end gap-6 px-6 py-6 text-sm text-muted-2">
        <Link
          href="/impressum"
          className="rounded-sm transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
        >
          Impressum
        </Link>
        <Link
          href="/login"
          className="rounded-sm transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
        >
          Anmelden
        </Link>
      </footer>
    </div>
  );
}
