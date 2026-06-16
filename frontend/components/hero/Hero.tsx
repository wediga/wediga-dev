"use client";

// The landing hero: an unordered mass of atoms forms into a stilisiertes star
// system on load, then a scroll-driven on-rails camera rides from planet to
// planet. Ported unchanged in feel from the approved /hero-lab sandbox; the
// engine and its motion constants are the frozen contract.

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import type { EngineHandle } from "./engine/types";

// Subscribe to prefers-reduced-motion the React way: SSR-safe (server snapshot is
// false), no setState-in-effect, and it follows live changes to the setting.
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mq = window.matchMedia(REDUCED_MOTION_QUERY);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => false,
  );
}

// three touches browser-only globals, so the engine is imported lazily inside the
// effect. That keeps the page server-renderable and code-splits the heavy bundle.

// Fixed in production: the approved configuration is 120k individual lit points.
const ATOM_COUNT = 120000;

// Placeholder station copy in fixed section order. Which planet carries which is
// randomised per load inside the engine. The real BFF content lives in the
// readable layer (see LandingContent); mapping it onto these stations is Phase H2.
const SECTIONS = [
  {
    title: "Alexander Wedig",
    eyebrow: "Intro",
    body: "ML Engineer. Aus rohen Daten wird geordnete Information, und genau das zeigt dieser Hero, sobald sich die Atome zum System ordnen.",
  },
  {
    title: "Über mich",
    eyebrow: "About",
    body: "Platzhalter. Ein paar Sätze über Hintergrund und Arbeitsweise, ruhig und lesbar, der echte Text kommt aus der BFF.",
  },
  {
    title: "Werkzeuge",
    eyebrow: "Toolkit",
    body: "Platzhalter. Die Werkzeuge und Modelle, mit denen ich arbeite, als kurze geordnete Liste statt als Schlagwortwolke.",
  },
  {
    title: "Zugang",
    eyebrow: "Zugang",
    body: "Platzhalter. Die persönlichen Inhalte liegen hinter Zugang, erreichbar über Login oder den persönlichen Link.",
  },
];

function randomSeed() {
  return Math.floor(Math.random() * 1_000_000);
}

export function Hero({ readable }: { readable: React.ReactNode }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const engineRef = useRef<EngineHandle | null>(null);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const activeRef = useRef(-1);

  // A fresh system per load. Not rendered into markup, so no hydration mismatch.
  const [seed] = useState(randomSeed);
  const reducedMotion = usePrefersReducedMotion();
  // Active station drives which title gets the assemble animation. It changes only
  // a few times, so it is React state; the per-frame reveal is written to the DOM
  // directly in the callback to avoid re-rendering every frame.
  const [active, setActive] = useState(-1);

  // Build / rebuild the engine when the seed or the motion preference changes.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let cancelled = false;
    let handle: EngineHandle | null = null;

    const onStation = (
      index: number,
      docked: number,
      sx: number,
      sy: number,
      screenR: number,
    ) => {
      if (cancelled) return;
      const refs = sectionRefs.current;
      for (let i = 0; i < refs.length; i++) {
        const el = refs[i];
        if (!el) continue;
        if (i === index) {
          // Box centre exactly on the planet's projected centre: the planet centre
          // sits in the middle of the text box and the box tracks it as it drifts.
          el.style.left = `${sx}px`;
          el.style.top = `${sy}px`;
          el.style.opacity = String(Math.min(1, docked));
          // Size the scrim to the actual projected planet: a true square keyed to
          // the disc radius, so the circular darkening covers the whole planet and
          // fades out just past its rim.
          const scrim = el.firstElementChild as HTMLElement | null;
          if (scrim) {
            const side = `${Math.round(screenR * 2)}px`;
            scrim.style.width = side;
            scrim.style.height = side;
          }
        } else {
          el.style.opacity = "0";
        }
      }
      if (activeRef.current !== index) {
        activeRef.current = index;
        setActive(index);
      }
    };

    (async () => {
      try {
        const { createWebglEngine } = await import("./engine/webglEngine");
        handle = await createWebglEngine(
          canvas,
          { atomCount: ATOM_COUNT, seed, reducedMotion },
          { onStation },
        );
      } catch {
        return;
      }
      if (cancelled) {
        handle?.dispose();
        return;
      }
      engineRef.current = handle;
    })();

    return () => {
      cancelled = true;
      handle?.dispose();
      engineRef.current = null;
    };
  }, [seed, reducedMotion]);

  // Reset the scroll on a rebuild so the ride always starts at the overview.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [seed, reducedMotion]);

  // Hard scroll-snap onto each stop so the wheel locks on a station instead of
  // leaving you in an in-between, only while the rails (full motion) are active.
  useEffect(() => {
    if (reducedMotion) return;
    const el = document.documentElement;
    const prev = el.style.scrollSnapType;
    el.style.scrollSnapType = "y mandatory";
    return () => {
      el.style.scrollSnapType = prev;
    };
  }, [reducedMotion]);

  return (
    <main className="relative bg-[#05060a] text-zinc-200">
      <style>{`
        @keyframes heroAssemble {
          from { opacity: 0; filter: blur(10px); transform: translateY(10px) scale(0.98); letter-spacing: 0.3em; }
          to { opacity: 1; filter: blur(0); transform: none; letter-spacing: normal; }
        }
        .hero-assemble { animation: heroAssemble 760ms cubic-bezier(0.16,1,0.3,1) both; }
        @media (prefers-reduced-motion: reduce) {
          .hero-assemble { animation: none; }
        }
      `}</style>

      <canvas
        ref={canvasRef}
        className="fixed inset-0 h-full w-full"
        aria-hidden="true"
      />

      {reducedMotion ? (
        // Flat, fully readable column over the formed still frame. No camera, no
        // rails: the real content is the page.
        <div className="relative z-10 min-h-screen bg-[#05060a]/92 backdrop-blur-sm">
          {readable}
          <SiteFooter className="mx-auto max-w-2xl px-6 pb-16" />
        </div>
      ) : (
        <>
          {/* The real BFF content stays in the DOM behind the canvas: present for
              screen readers, search engines and the E2E suite while the ride plays.
              Phase H2 surfaces it into the visible section planets. */}
          <div
            className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
            aria-hidden="false"
          >
            {readable}
          </div>

          {/* Placeholder station text, real DOM text positioned on the active
              planet via its projected screen coordinates, with a soft scrim behind
              for legibility. Only the active station is shown. */}
          <div className="pointer-events-none fixed inset-0 z-10">
            {SECTIONS.map((s, i) => (
              <div
                key={s.eyebrow}
                ref={(el) => {
                  sectionRefs.current[i] = el;
                }}
                style={{ opacity: 0, left: "50%", top: "50%" }}
                className="absolute w-[min(82vw,420px)] -translate-x-1/2 -translate-y-1/2 text-center transition-opacity duration-200"
              >
                {/* Scrim: a circular darkening over the whole opened planet, darkest
                    at the centre and fading out before the rim, so the busy interior
                    points calm down and the eye rests on the text while the lit rim
                    stays visible. */}
                <div
                  aria-hidden="true"
                  className="absolute left-1/2 top-1/2 -z-10 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    background:
                      "radial-gradient(circle closest-side at center, rgba(5,6,10,1) 0%, rgba(5,6,10,0.99) 48%, rgba(5,6,10,0.92) 72%, rgba(5,6,10,0.72) 90%, rgba(5,6,10,0) 100%)",
                  }}
                />
                <h2
                  key={active === i ? `${i}-on` : `${i}-off`}
                  className={`text-4xl font-medium tracking-[-0.02em] text-white ${
                    active === i ? "hero-assemble" : ""
                  }`}
                >
                  {s.title}
                </h2>
                <p className="mx-auto mt-4 max-w-sm text-[15px] leading-relaxed text-zinc-100">
                  {s.body}
                </p>
              </div>
            ))}
          </div>

          {/* Scroll track: one full-viewport snap section per stop (overview first,
              then one per station), so the wheel locks onto a station instead of
              leaving you in an in-between. The camera reads scrollY in the frame. */}
          {Array.from({ length: SECTIONS.length + 1 }).map((_, i) => (
            <div
              key={i}
              aria-hidden="true"
              className="h-screen"
              style={{ scrollSnapAlign: "start", scrollSnapStop: "always" }}
            />
          ))}

          {/* Impressum and Login stay reachable throughout the ride. */}
          <SiteFooter className="fixed inset-x-0 bottom-0 z-20 flex justify-center gap-5 pb-5" />
        </>
      )}
    </main>
  );
}

function SiteFooter({ className }: { className?: string }) {
  return (
    <footer
      className={`flex gap-5 text-sm text-zinc-400 ${className ?? ""}`}
    >
      <Link href="/impressum" className="transition-colors hover:text-white">
        Impressum
      </Link>
      <Link href="/login" className="transition-colors hover:text-white">
        Login
      </Link>
    </footer>
  );
}
