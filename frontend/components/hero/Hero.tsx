"use client";

// The landing hero: atoms assemble into a stylized star system, then a
// scroll-driven on-rails camera rides planet to planet. The engine and its
// motion constants are a frozen contract, so changes touch only the content on
// the planets. This shell is state, wiring and render; the lifecycle and scroll
// behaviour live in hooks, the station text in StationsOverlay, the two
// appearances in their own components. hero-assemble and hero-rise keyframes are
// in globals.css.

import type { SkillCategory } from "@/lib/types";
import { useMotionMode } from "@/lib/useMotionMode";
import { QuietLanding } from "./QuietLanding";
import { SiteFooter } from "./SiteFooter";
import { StationsOverlay } from "./StationsOverlay";
import { STATIONS } from "./stations";
import { useHeroEngine } from "./useHeroEngine";
import { useScrollReset, useScrollSnap } from "./useHeroScroll";

export function Hero({
  readable,
  skills,
  isRecruiter,
}: {
  readable: React.ReactNode;
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  // The on-page switch wins over the OS setting. Reduced motion swaps the whole
  // hero for the quiet sun-anchored landing.
  const reducedMotion = useMotionMode() === "reduced";

  // scroll-reset shares the engine's [seed, reducedMotion] so a rebuild restarts
  // at the overview; scroll-snap runs only during the ride.
  const { canvasRef, sectionRefs, seed, active } = useHeroEngine(reducedMotion);
  useScrollReset(seed, reducedMotion);
  useScrollSnap(reducedMotion);

  return (
    <main className="relative bg-bg text-ink">
      {reducedMotion ? (
        // Its own design, not the ride pushed back: a cursor-reactive sun anchors
        // one side while the same public content reads down a column beside it.
        <QuietLanding
          canvasRef={canvasRef}
          skills={skills}
          isRecruiter={isRecruiter}
        />
      ) : (
        <>
          <canvas
            ref={canvasRef}
            className="fixed inset-0 h-full w-full"
            aria-hidden="true"
          />

          {/* The real BFF content stays in the DOM behind the canvas, the
              accessible source of truth for screen readers, search engines and
              the E2E suite while the ride plays. The visible stations below are
              its visual duplicate. */}
          <div
            className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
            aria-hidden="false"
          >
            {readable}
          </div>

          {/* Visible station text positioned on the active planet via its
              projected screen coordinates. Only the active station shows. */}
          <StationsOverlay
            sectionRefs={sectionRefs}
            active={active}
            skills={skills}
            isRecruiter={isRecruiter}
          />

          {/* Scroll track: one full-viewport snap section per stop (overview,
              then one per station), so the wheel locks onto a station. The camera
              reads scrollY in the frame. */}
          {Array.from({ length: STATIONS.length + 1 }).map((_, i) => (
            <div
              key={i}
              aria-hidden="true"
              className="h-screen"
              style={{ scrollSnapAlign: "start", scrollSnapStop: "always" }}
            />
          ))}

          {/* Impressum and the motion switch stay reachable during the ride. */}
          <SiteFooter variant="fixed" />
        </>
      )}
    </main>
  );
}
