import type { CSSProperties } from "react";
import { getPortfolio } from "@/lib/content";
import { PortfolioTiles } from "@/components/portfolio/PortfolioTiles";

export default async function PortfolioPage() {
  const tiles = await getPortfolio();

  return (
    <div>
      <header className="reveal" style={{ "--reveal-i": "0" } as CSSProperties}>
        <h1 className="text-[clamp(2.2rem,4.5vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.02em] text-balance">
          Portfolio
        </h1>
        <p className="mt-4 max-w-[60ch] text-pretty leading-relaxed text-muted">
          Ausgewählte Projekte, kuratiert für den Einblick in Arbeitsweise und
          Stack.
        </p>
      </header>

      <section className="mt-16" aria-labelledby="projects-heading">
        <h2
          id="projects-heading"
          className="reveal font-mono text-xs uppercase tracking-[0.16em] text-muted-2"
          style={{ "--reveal-i": "1" } as CSSProperties}
        >
          Ausgewählte Projekte
        </h2>

        {tiles.length === 0 ? (
          <p className="mt-6 leading-relaxed text-muted">
            Noch keine Projekte hinterlegt.
          </p>
        ) : (
          <PortfolioTiles tiles={tiles} />
        )}
      </section>
    </div>
  );
}
