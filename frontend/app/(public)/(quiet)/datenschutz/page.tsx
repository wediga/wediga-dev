import type { Metadata } from "next";
import { getImpressum } from "@/lib/content";
import { ACCENT_LINK } from "@/components/site/SiteChrome";
import {
  PRIVACY_POLICY_DATE,
  PRIVACY_SECTIONS,
} from "./sections";

export const metadata: Metadata = {
  title: "Datenschutz",
};

const HEADING = "text-lg font-medium text-ink";
const PARAGRAPH = "mt-3 leading-relaxed text-muted";

// The privacy policy. Name and email of the person responsible come from the
// impressum, so they are kept in one place; the rest is the fixed text.
export default async function DatenschutzPage() {
  const impressum = await getImpressum();

  return (
    <div className="quiet-enter w-full max-w-2xl">
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-ink">
        Datenschutzerklärung
      </h1>

      <section className="mt-10">
        <h2 className={HEADING}>Wer verantwortlich ist</h2>
        {impressum ? (
          <p className={PARAGRAPH}>
            Verantwortlich für die Verarbeitung deiner Daten auf dieser Website
            ist {impressum.name}, erreichbar unter{" "}
            <a href={`mailto:${impressum.email}`} className={ACCENT_LINK}>
              {impressum.email}
            </a>
            . Einen Datenschutzbeauftragten gibt es nicht, weil keine Pflicht
            dazu besteht. Bei Fragen zum Datenschutz schreibst du mir einfach an
            diese Adresse.
          </p>
        ) : (
          <p className={PARAGRAPH}>Noch kein Impressum hinterlegt.</p>
        )}
      </section>

      {PRIVACY_SECTIONS.map((section) => (
        <section key={section.heading} className="mt-10">
          <h2 className={HEADING}>{section.heading}</h2>
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph} className={PARAGRAPH}>
              {paragraph}
            </p>
          ))}
        </section>
      ))}

      <p className="mt-12 text-sm text-muted-2">Stand: {PRIVACY_POLICY_DATE}</p>
    </div>
  );
}
