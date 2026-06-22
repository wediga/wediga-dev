import { getContact } from "@/lib/content";
import { safeHref } from "@/lib/url";
import { ACCENT_LINK } from "@/components/site/SiteChrome";

export default async function ContactPage() {
  const contact = await getContact();

  const github = safeHref(contact?.github);
  const linkedin = safeHref(contact?.linkedin);

  return (
    <div>
      <header className="reveal" style={{ "--reveal-i": "0" } as React.CSSProperties}>
        <h1 className="text-[clamp(2.2rem,4.5vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.02em] text-balance">
          Kontakt
        </h1>
        <p className="mt-4 max-w-[60ch] text-pretty leading-relaxed text-muted">
          Der direkte Draht. Für Rückfragen oder ein Gespräch genügt eine
          E-Mail.
        </p>
      </header>

      {contact ? (
        <dl className="mt-12 grid max-w-3xl grid-cols-1 gap-x-12 sm:grid-cols-2">
          <Field label="Name" reveal={1}>
            <span className="text-ink">{contact.name}</span>
          </Field>
          <Field label="E-Mail" reveal={2}>
            <a href={`mailto:${contact.email}`} className={ACCENT_LINK}>
              {contact.email}
            </a>
          </Field>
          {github ? (
            <Field label="GitHub" reveal={3}>
              <a href={github} className={ACCENT_LINK} rel="noreferrer noopener">
                {contact.github}
              </a>
            </Field>
          ) : null}
          {linkedin ? (
            <Field label="LinkedIn" reveal={4}>
              <a href={linkedin} className={ACCENT_LINK} rel="noreferrer noopener">
                {contact.linkedin}
              </a>
            </Field>
          ) : null}
        </dl>
      ) : (
        <div
          className="reveal mt-12 max-w-[60ch] rounded-md border border-line bg-surface px-7 py-10"
          style={{ "--reveal-i": "1" } as React.CSSProperties}
        >
          <p className="leading-relaxed text-muted">
            Noch keine Kontaktdaten hinterlegt.
          </p>
        </div>
      )}
    </div>
  );
}

// One labelled contact row. The hairline above each row groups them into a quiet
// table that runs in two columns on wider screens and stacks on narrow.
function Field({
  label,
  reveal,
  children,
}: {
  label: string;
  reveal: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="reveal border-t border-line py-5"
      style={{ "--reveal-i": String(reveal) } as React.CSSProperties}
    >
      <dt className="font-mono text-xs uppercase tracking-[0.14em] text-muted-2">
        {label}
      </dt>
      <dd className="mt-1.5 leading-relaxed">{children}</dd>
    </div>
  );
}
