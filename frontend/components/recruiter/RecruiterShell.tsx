import Link from "next/link";
import { INTRO } from "@/components/hero/content";
import { RecruiterNav } from "./RecruiterNav";
import { GenerativeAccents } from "./GenerativeAccents";

// The shared chrome around the three recruiter views. Dark and consistent with
// the quiet public pages, it carries navigation between the views and a way back
// to the landing (the brand wordmark). It sits inside the gate in
// (recruiter)/layout.tsx, which is untouched; this is presentation only.
//
// Layout: a sticky single-line header, a wide content area that lets each view
// use the full canvas (the views cap their own prose), and a quiet footer. The
// generative accent is wired once here for every view underneath.
export function RecruiterShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <GenerativeAccents />

      <header className="sticky top-0 z-[var(--z-nav)] border-b border-line bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-6 py-4 sm:gap-6 lg:px-10">
          <Link
            href="/"
            className="quiet-press rounded-sm text-sm font-medium tracking-[-0.02em] text-ink transition-colors hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
          >
            {INTRO.name}
          </Link>
          <RecruiterNav />
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1600px] flex-1 px-6 pb-28 pt-[clamp(2.5rem,6vh,5rem)] lg:px-10">
        {children}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-[1600px] items-center justify-end gap-6 px-6 py-6 text-sm text-muted-2 lg:px-10">
          <Link
            href="/impressum"
            className="rounded-sm transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
          >
            Impressum
          </Link>
          <Link
            href="/"
            className="rounded-sm transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
          >
            Zur Startseite
          </Link>
        </div>
      </footer>
    </div>
  );
}
