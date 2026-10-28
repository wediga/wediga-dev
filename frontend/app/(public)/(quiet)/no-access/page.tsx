import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Kein Zugang",
};

// Where a login through authentik lands when the account is in none of the
// groups that wediga.dev knows. No session is created for it.
export default function NoAccessPage() {
  return (
    <div className="quiet-enter w-full max-w-md">
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-ink">
        Kein Zugang
      </h1>
      <p className="mt-4 leading-relaxed text-muted">
        Mit diesem Konto gibt es hier keinen Zugang.
      </p>
      <div className="mt-10">
        <Link
          href="/"
          className="quiet-press inline-flex rounded-md border border-muted-2/50 px-6 py-2.5 text-sm uppercase tracking-[0.14em] text-ink transition-colors hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
        >
          Zur Startseite
        </Link>
      </div>
    </div>
  );
}
