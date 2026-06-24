"use client";

// The landing hero: an unordered mass of atoms forms into a stilisiertes star
// system on load, then a scroll-driven on-rails camera rides from planet to
// planet. Ported unchanged in feel from the approved /hero-lab sandbox; the
// engine and its motion constants are the frozen contract. Phase H2 changes only
// the content carried on the planets, not the camera, scrim, spring or timing.
//
// This shell is only state, wiring and render: the engine lifecycle and the
// scroll behaviour live in hooks (useHeroEngine, useScrollReset, useScrollSnap),
// the visible station text in StationsOverlay, and the two appearances
// (full-motion ride, quiet landing) in their own components. The keyframes for
// hero-assemble and hero-rise live in globals.css with the site's other reveals.

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
  // The resolved site-wide motion mode (the on-page switch wins over the OS
  // setting). Reduced motion swaps the whole hero for the quiet, sun-anchored
  // landing instead of the scroll-driven ride.
  const reducedMotion = useMotionMode() === "reduced";

  // The engine lifecycle owns the canvas and section refs and the active station;
  // the scroll-reset shares the engine's [seed, reducedMotion] so a rebuild always
  // restarts at the overview, and scroll-snap is active only during the ride.
  const { canvasRef, sectionRefs, seed, active } = useHeroEngine(reducedMotion);
  useScrollReset(seed, reducedMotion);
  useScrollSnap(reducedMotion);

  return (
    <main className="relative bg-bg text-ink">
      {reducedMotion ? (
        // The quiet landing: its own design, not the ride pushed back. A living,
        // cursor-reactive sun anchors one side while the same public content
        // (intro teaser, toolkit, access door) reads down a calm column beside it.
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

          {/* The real BFF content stays in the DOM behind the canvas: present for
              screen readers, search engines and the E2E suite while the ride
              plays. It is the accessible source of truth; the visible stations
              below are its visual duplicate. */}
          <div
            className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
            aria-hidden="false"
          >
            {readable}
          </div>

          {/* Visible station text, real DOM text positioned on the active planet
              via its projected screen coordinates, with a soft scrim behind for
              legibility. Only the active station is shown. */}
          <StationsOverlay
            sectionRefs={sectionRefs}
            active={active}
            skills={skills}
            isRecruiter={isRecruiter}
          />

          {/* Scroll track: one full-viewport snap section per stop (overview first,
              then one per station), so the wheel locks onto a station instead of
              leaving you in an in-between. The camera reads scrollY in the frame. */}
          {Array.from({ length: STATIONS.length + 1 }).map((_, i) => (
            <div
              key={i}
              aria-hidden="true"
              className="h-screen"
              style={{ scrollSnapAlign: "start", scrollSnapStop: "always" }}
            />
          ))}

          {/* Impressum, Login and the motion switch stay reachable throughout the
              ride. */}
          <SiteFooter variant="fixed" />
        </>
      )}
    </main>
  );
}
