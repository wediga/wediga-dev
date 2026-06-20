import { getCvStatus } from "@/lib/content";

// The recruiter CV view. The CV is a single uploaded PDF, so this page offers
// the download and an inline preview of that same file, both served through the
// gated BFF download route. On wide screens the action sits in a sidebar beside
// the preview; on narrow it stacks above. A clean empty state covers no CV yet.
export default async function CvPage() {
  const { present } = await getCvStatus();

  return (
    <div>
      <header className="reveal" style={{ "--reveal-i": "0" } as React.CSSProperties}>
        <h1 className="text-[clamp(2.2rem,4.5vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.02em] text-balance">
          Lebenslauf
        </h1>
        <p className="mt-4 max-w-[60ch] text-pretty leading-relaxed text-muted">
          Der vollständige Lebenslauf als PDF, direkt herunterladbar oder hier in
          der Vorschau.
        </p>
      </header>

      {present ? (
        <div className="mt-12 grid gap-10 lg:grid-cols-[300px_minmax(0,1fr)] lg:items-start">
          <aside
            className="reveal lg:sticky lg:top-28"
            style={{ "--reveal-i": "1" } as React.CSSProperties}
          >
            <a
              href="/api/cv/download"
              className="quiet-press inline-flex items-center justify-center rounded-md bg-accent px-6 py-2.5 text-sm font-medium tracking-[0.02em] text-bg transition-[transform,filter] hover:brightness-105 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
            >
              Als PDF herunterladen
            </a>
            <p className="mt-4 text-sm leading-relaxed text-muted-2">
              PDF, öffnet im Download. Die Vorschau rechts zeigt dieselbe Datei.
            </p>
          </aside>

          <div
            className="reveal overflow-hidden rounded-md border border-line bg-surface"
            style={{ "--reveal-i": "2" } as React.CSSProperties}
          >
            <object
              data="/api/cv/download?inline=1"
              type="application/pdf"
              className="h-[clamp(440px,80vh,1040px)] w-full"
              aria-label="Lebenslauf, Vorschau"
            >
              <p className="p-6 text-sm leading-relaxed text-muted">
                Die Vorschau kann nicht angezeigt werden. Nutzen Sie den Download.
              </p>
            </object>
          </div>
        </div>
      ) : (
        <div
          className="reveal mt-12 max-w-[60ch] rounded-md border border-line bg-surface px-7 py-10"
          style={{ "--reveal-i": "1" } as React.CSSProperties}
        >
          <p className="leading-relaxed text-muted">
            Noch kein Lebenslauf hinterlegt. Sobald ein PDF vorliegt, erscheint es
            hier zum Ansehen und Herunterladen.
          </p>
        </div>
      )}
    </div>
  );
}
