import type { Metadata } from "next";
import { getImpressum } from "@/lib/content";

export const metadata: Metadata = {
  title: "Impressum",
};

// The public impressum shows only name and email. The full legal details
// (address and links) sit behind the recruiter view, which gates them by
// session. The read here is unchanged; only the presentation moved into the
// quiet dark shell.
export default async function ImpressumPage() {
  const impressum = await getImpressum();

  return (
    <div className="quiet-enter w-full max-w-xl">
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-ink">
        Impressum
      </h1>

      {impressum ? (
        <dl className="mt-10 divide-y divide-line border-y border-line">
          <div className="grid grid-cols-1 gap-1 py-4 sm:grid-cols-[7rem_1fr] sm:gap-4">
            <dt className="text-xs uppercase tracking-[0.14em] text-muted">
              Name
            </dt>
            <dd className="text-ink">{impressum.name}</dd>
          </div>
          <div className="grid grid-cols-1 gap-1 py-4 sm:grid-cols-[7rem_1fr] sm:gap-4">
            <dt className="text-xs uppercase tracking-[0.14em] text-muted">
              E-Mail
            </dt>
            <dd>
              <a
                href={`mailto:${impressum.email}`}
                className="rounded-sm break-words text-accent underline decoration-accent/40 underline-offset-4 transition-colors hover:decoration-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
              >
                {impressum.email}
              </a>
            </dd>
          </div>
        </dl>
      ) : (
        <p className="mt-6 leading-relaxed text-muted">
          Noch kein Impressum hinterlegt.
        </p>
      )}
    </div>
  );
}
