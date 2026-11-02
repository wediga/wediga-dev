import type { Metadata } from "next";
import { Portrait } from "@/components/Portrait";
import { INTRO } from "@/components/hero/content";
import { getCard, getPortraitCrop } from "@/lib/content";
import { LINK_LABELS, type LinkKind } from "@/lib/types";

// The page behind the QR code: who I am, every way to reach me and the
// contact to save in one tap. It shows phone and email, so search engines are
// asked to leave it out.
export const metadata: Metadata = {
  title: "Kontakt",
  robots: { index: false, follow: false },
};

const VCARD_SRC = "/api/card/vcard";

// The order of the links on the page, the most useful one at a fair first.
const LINK_ORDER: LinkKind[] = ["linkedin", "github", "website"];

const BUTTON =
  "quiet-press block w-full rounded-md border px-5 py-3 text-center text-sm uppercase tracking-[0.12em] transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60";
const PRIMARY = `${BUTTON} border-accent bg-accent text-bg hover:bg-accent/90`;
const SECONDARY = `${BUTTON} border-line text-ink hover:border-accent hover:bg-accent/10`;

// A tel: link takes the digits and a leading plus, the separators are only
// for reading.
function telHref(phone: string): string {
  return `tel:${phone.replace(/[^+\d]/g, "")}`;
}

export default async function HiPage() {
  const [card, crop] = await Promise.all([getCard(), getPortraitCrop()]);

  if (!card) {
    return <p className="text-muted">Noch keine Kontaktdaten hinterlegt.</p>;
  }

  const links = LINK_ORDER.flatMap((kind) => {
    const url = card.links[kind];

    return url ? [{ kind, url }] : [];
  });

  return (
    <div className="quiet-enter flex w-full max-w-sm flex-col items-center text-center">
      {crop ? <Portrait crop={crop} alt={card.name} className="h-32 w-32 rounded-full" /> : null}
      <h1 className="mt-6 text-[clamp(2rem,8vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-ink">
        {card.name}
      </h1>
      <p className="mt-3 font-mono text-xs uppercase tracking-[0.14em] text-muted">{INTRO.role}</p>

      <nav aria-label="Kontakt" className="mt-10 flex w-full flex-col gap-3">
        <a href={VCARD_SRC} download className={PRIMARY}>
          Kontakt speichern
        </a>
        <a href={`mailto:${card.email}`} className={SECONDARY}>
          E-Mail schreiben
        </a>
        {card.phone ? (
          <a href={telHref(card.phone)} className={SECONDARY}>
            Anrufen
          </a>
        ) : null}
        {links.map((link) => (
          <a key={link.kind} href={link.url} rel="noreferrer" className={SECONDARY}>
            {LINK_LABELS[link.kind]}
          </a>
        ))}
      </nav>
    </div>
  );
}
