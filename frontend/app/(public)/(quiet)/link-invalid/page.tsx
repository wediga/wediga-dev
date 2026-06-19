import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Link nicht mehr gültig",
};

// The dead end a failed magic-link redeem lands on. A calm, friendly close with
// one clear way back to the landing. No behaviour changed; this is the same
// route the redeem handler redirects to, now in the quiet dark shell.
export default function LinkInvalidPage() {
  return (
    <div className="quiet-enter w-full max-w-md">
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-white">
        Link nicht mehr gültig
      </h1>
      <p className="mt-4 leading-relaxed text-zinc-300">
        Dieser Zugangslink ist abgelaufen oder wurde zurückgezogen. Bitte fragen
        Sie nach einem neuen Link.
      </p>
      <div className="mt-10">
        <Link
          href="/"
          className="quiet-press inline-flex rounded-md border border-white/25 px-6 py-2.5 text-sm uppercase tracking-[0.14em] text-white transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white/60"
        >
          Zur Startseite
        </Link>
      </div>
    </div>
  );
}
