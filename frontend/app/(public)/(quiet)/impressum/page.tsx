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
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-white">
        Impressum
      </h1>

      {impressum ? (
        <dl className="mt-10 divide-y divide-white/10 border-y border-white/10">
          <div className="grid grid-cols-1 gap-1 py-4 sm:grid-cols-[7rem_1fr] sm:gap-4">
            <dt className="text-xs uppercase tracking-[0.14em] text-zinc-400">
              Name
            </dt>
            <dd className="text-zinc-100">{impressum.name}</dd>
          </div>
          <div className="grid grid-cols-1 gap-1 py-4 sm:grid-cols-[7rem_1fr] sm:gap-4">
            <dt className="text-xs uppercase tracking-[0.14em] text-zinc-400">
              E-Mail
            </dt>
            <dd>
              <a
                href={`mailto:${impressum.email}`}
                className="rounded-sm break-words text-zinc-100 underline decoration-white/30 underline-offset-4 transition-colors hover:decoration-white/70 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white/60"
              >
                {impressum.email}
              </a>
            </dd>
          </div>
        </dl>
      ) : (
        <p className="mt-6 leading-relaxed text-zinc-400">
          Noch kein Impressum hinterlegt.
        </p>
      )}
    </div>
  );
}
