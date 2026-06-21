"use client";

// The landing hero: an unordered mass of atoms forms into a stilisiertes star
// system on load, then a scroll-driven on-rails camera rides from planet to
// planet. Ported unchanged in feel from the approved /hero-lab sandbox; the
// engine and its motion constants are the frozen contract. Phase H2 changes only
// the content carried on the planets, not the camera, scrim, spring or timing.

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { EngineHandle } from "./engine/types";
import type { SkillCategory } from "@/lib/types";
import { useMotionMode } from "@/lib/useMotionMode";
import { MotionToggle } from "@/components/MotionToggle";
import { INTRO, LANDING, accessLead } from "./content";
import { AccessButton } from "./LandingContent";

// three touches browser-only globals, so the engine is imported lazily inside the
// effect. That keeps the page server-renderable and code-splits the heavy bundle.

// Fixed in production: the approved configuration is 120k individual lit points.
const ATOM_COUNT = 120000;

// Public landing stations, in fixed order: an intro teaser, a toolkit planet that
// carries the real skills, and the access door. Sparse on purpose: the public
// page is a teaser, the depth lives behind the recruiter login. One planet
// anchors each station, and the engine is told the count so it always has enough
// planets. The order is fixed; which planet holds which station is generative.
type StationKind = "intro" | "toolkit" | "access";
const STATIONS: StationKind[] = ["intro", "toolkit", "access"];

function randomSeed() {
  return Math.floor(Math.random() * 1_000_000);
}

export function Hero({
  readable,
  skills,
  isRecruiter,
}: {
  readable: React.ReactNode;
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const engineRef = useRef<EngineHandle | null>(null);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const activeRef = useRef(-1);

  // A fresh system per load. Not rendered into markup, so no hydration mismatch.
  const [seed] = useState(randomSeed);
  // The resolved site-wide motion mode (the on-page switch wins over the OS
  // setting). Reduced motion swaps the whole hero for the quiet, sun-anchored
  // landing instead of the scroll-driven ride.
  const reducedMotion = useMotionMode() === "reduced";
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
          {
            atomCount: ATOM_COUNT,
            seed,
            reducedMotion,
            stationCount: STATIONS.length,
          },
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
      // Hand the generated system colours to the rest of the site (read-only).
      // The recruiter and quiet views read this snapshot to colour their
      // generative accent; without it they fall back to the crimson accent.
      try {
        sessionStorage.setItem(
          "hero:system-colors",
          JSON.stringify(handle.systemColors),
        );
      } catch {
        // sessionStorage can be unavailable (privacy mode); the accent then
        // simply falls back to crimson, so this is safe to ignore.
      }
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

  const titleClass = (i: number) =>
    `text-[clamp(2rem,6vh,4.5rem)] font-medium leading-[1.05] tracking-[-0.02em] text-white ${
      active === i ? "hero-assemble" : ""
    }`;

  return (
    <main className="relative bg-bg text-ink">
      <style>{`
        @keyframes heroAssemble {
          from { opacity: 0; filter: blur(10px); transform: translateY(10px) scale(0.98); letter-spacing: 0.3em; }
          to { opacity: 1; filter: blur(0); transform: none; letter-spacing: normal; }
        }
        .hero-assemble { animation: heroAssemble 760ms cubic-bezier(0.16,1,0.3,1) both; }
        /* Content reveal bound to the existing dock moment: the toolkit groups
           rise in a short stagger as the station opens. It rides the camera and
           scrim timing, it does not change them. */
        @keyframes heroRise {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: none; }
        }
        .hero-rise > * { opacity: 0; animation: heroRise 560ms cubic-bezier(0.16,1,0.3,1) both; }
        .hero-rise > *:nth-child(1) { animation-delay: 40ms; }
        .hero-rise > *:nth-child(2) { animation-delay: 100ms; }
        .hero-rise > *:nth-child(3) { animation-delay: 160ms; }
        .hero-rise > *:nth-child(4) { animation-delay: 220ms; }
        .hero-rise > *:nth-child(5) { animation-delay: 280ms; }
        .hero-rise > *:nth-child(6) { animation-delay: 340ms; }
        .hero-rise > *:nth-child(7) { animation-delay: 400ms; }
        .hero-rise > *:nth-child(8) { animation-delay: 460ms; }
        /* Physical press feedback on the access door. */
        .hero-door { transition: transform 160ms cubic-bezier(0.16,1,0.3,1), background-color 200ms ease; }
        .hero-door:active { transform: scale(0.97); }
        @media (prefers-reduced-motion: reduce) {
          .hero-assemble { animation: none; }
          .hero-rise > * { animation: none; opacity: 1; }
          .hero-door { transition: background-color 200ms ease; }
          .hero-door:active { transform: none; }
        }
      `}</style>

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
              legibility. Only the active station is shown. The whole overlay is a
              visual duplicate of the readable layer, so it is aria-hidden and its
              controls are out of the tab order; mouse users still click the door. */}
          <div className="pointer-events-none fixed inset-0 z-10" aria-hidden="true">
            {STATIONS.map((kind, i) => (
              <div
                key={kind}
                ref={(el) => {
                  sectionRefs.current[i] = el;
                }}
                style={{ opacity: 0, left: "50%", top: "50%" }}
                className="absolute w-[min(86vw,560px)] -translate-x-1/2 -translate-y-1/2 text-center transition-opacity duration-200"
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

                {kind === "intro" ? (
                  <>
                    {/* Small self-hosted portrait; the next/image optimizer is
                        needless for an 88 KB asset and flaky in dev, so a plain img
                        is cleaner. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/portrait.jpg"
                      alt="Alexander Wedig"
                      width={56}
                      height={56}
                      className="mx-auto mb-[2vh] h-[clamp(4rem,11vh,8rem)] w-[clamp(4rem,11vh,8rem)] rounded-full object-cover"
                    />
                    <h2 key={active === i ? `${i}-on` : `${i}-off`} className={titleClass(i)}>
                      {INTRO.name}
                    </h2>
                    <p className="mt-[1vh] text-[clamp(0.72rem,1.5vh,1.05rem)] uppercase tracking-[0.12em] text-zinc-400">
                      {INTRO.role}
                    </p>
                    <p className="mx-auto mt-[1.8vh] max-w-md text-[clamp(1rem,2.4vh,1.6rem)] leading-relaxed text-zinc-100">
                      {INTRO.hook}
                    </p>
                  </>
                ) : null}

                {kind === "toolkit" ? (
                  <>
                    <h2 key={active === i ? `${i}-on` : `${i}-off`} className={titleClass(i)}>
                      {LANDING.toolkitHeading}
                    </h2>
                    {skills.length > 0 ? (
                      <div
                        key={active === i ? `${i}-groups-on` : `${i}-groups-off`}
                        className="hero-rise mt-[2.2vh] flex flex-col items-center gap-[1.6vh]"
                      >
                        {skills.map((category) =>
                          category.skills.length === 0 ? null : (
                            <div key={category.id}>
                              <p className="text-[clamp(0.6rem,1.2vh,0.8rem)] uppercase tracking-[0.14em] text-zinc-400">
                                {category.name}
                              </p>
                              <ul className="mt-[0.8vh] flex flex-wrap justify-center gap-2">
                                {category.skills.map((skill) => (
                                  <li
                                    key={skill.id}
                                    className="rounded-full bg-white/[0.06] px-3 py-1 text-[clamp(0.78rem,1.7vh,1.05rem)] text-zinc-100"
                                  >
                                    {skill.name}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ),
                        )}
                      </div>
                    ) : null}
                  </>
                ) : null}

                {kind === "access" ? (
                  <>
                    <h2 key={active === i ? `${i}-on` : `${i}-off`} className={titleClass(i)}>
                      {LANDING.accessHeading}
                    </h2>
                    <p className="mx-auto mt-[1.8vh] max-w-md text-[clamp(1rem,2.4vh,1.6rem)] leading-relaxed text-zinc-100">
                      {accessLead(isRecruiter)}
                    </p>
                    <div className="pointer-events-auto mt-[2vh] flex justify-center">
                      <AccessButton isRecruiter={isRecruiter} decorative />
                    </div>
                  </>
                ) : null}
              </div>
            ))}
          </div>

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

// The quiet landing. A wide two-track layout: the public content reads down a
// left-aligned column in a calm, ordinary scroll, while the living sun sits big
// on the other track and stays in view (sticky) as you read. Real DOM text
// throughout, the same teaser, toolkit and access door as the full-motion ride,
// so both appearances say the same thing. The canvas hosts the engine's quiet
// render mode (the sun alone, cursor-reactive, no camera ride).
function QuietLanding({
  canvasRef,
  skills,
  isRecruiter,
}: {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  return (
    <div className="relative min-h-screen px-[max(28px,6vw)]">
      {/* The living sun. The screen splits in two: on wide screens the sun is
          fixed and stationary, centred in the RIGHT half (its centre at 75% of
          the width), a dominant anchor that does not move as the content scrolls.
          It is sized to stay within that right half, so it never crosses into the
          text. On narrow screens it sits in flow above the content (the full
          mobile pass is its own phase). The canvas is square so the sun stays
          round, and the engine keeps margin inside it so the cursor never clips. */}
      <div className="mx-auto mb-[2vh] flex aspect-square w-full max-w-[440px] items-center justify-center xl:fixed xl:left-3/4 xl:top-1/2 xl:z-0 xl:mx-0 xl:mb-0 xl:aspect-auto xl:h-[min(84vh,42vw)] xl:w-[min(84vh,42vw)] xl:max-w-none xl:-translate-x-1/2 xl:-translate-y-1/2">
        <canvas ref={canvasRef} className="h-full w-full" aria-hidden="true" />
      </div>

      {/* Content. The text column sits in the LEFT half, anchored to its right
          edge so it meets the centre line, with the sun centred in the right half
          beside it. The text itself is centre-aligned within that fixed column
          (centred heading, the lines overhanging evenly left and right), it is
          not pushed around in the half. An ordinary calm scroll; clears the
          pinned footer at the foot. */}
      <div className="relative z-10 pb-[16vh] pt-[4vh] xl:flex xl:w-1/2 xl:justify-end xl:pb-[20vh] xl:pr-[3vw] xl:pt-[15vh]">
        <div className="xl:w-[34rem] xl:text-center">
        <section>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/portrait.jpg"
            alt="Alexander Wedig"
            width={64}
            height={64}
            className="mb-8 h-28 w-28 rounded-full object-cover sm:h-32 sm:w-32 xl:mx-auto"
          />
          <h1 className="text-[clamp(2.4rem,4.4vw,4rem)] font-medium leading-[1.02] tracking-[-0.02em] text-ink text-balance">
            {INTRO.name}
          </h1>
          <p className="mt-4 font-mono text-sm uppercase tracking-[0.14em] text-muted">
            {INTRO.role}
          </p>
          <p className="mt-5 max-w-[20ch] text-[clamp(1.3rem,2.1vw,1.85rem)] leading-snug text-ink sm:max-w-[34ch] xl:mx-auto">
            {INTRO.hook}
          </p>
        </section>

        {skills.length > 0 ? (
          <section className="mt-[11vh]">
            <h2 className="text-[clamp(1.8rem,3vw,2.6rem)] font-medium tracking-[-0.02em] text-ink">
              {LANDING.toolkitHeading}
            </h2>
            <div className="mt-7 space-y-6">
              {skills.map((category) =>
                category.skills.length === 0 ? null : (
                  <div key={category.id}>
                    <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted-2">
                      {category.name}
                    </p>
                    <ul className="mt-2.5 flex flex-wrap gap-2 xl:justify-center">
                      {category.skills.map((skill) => (
                        <li
                          key={skill.id}
                          className="rounded-full bg-white/[0.06] px-4 py-1.5 font-mono text-sm text-ink"
                        >
                          {skill.name}
                        </li>
                      ))}
                    </ul>
                  </div>
                ),
              )}
            </div>
          </section>
        ) : null}

        <section className="mt-[11vh]">
          <h2 className="text-[clamp(1.8rem,3vw,2.6rem)] font-medium tracking-[-0.02em] text-ink">
            {LANDING.accessHeading}
          </h2>
          <p className="mt-4 max-w-[46ch] text-lg leading-relaxed text-muted xl:mx-auto">
            {accessLead(isRecruiter)}
          </p>
          <div className="mt-7">
            <AccessButton isRecruiter={isRecruiter} quiet />
          </div>
        </section>
        </div>
      </div>

      {/* Pinned to the bottom edge of the viewport, covering the sun behind it. */}
      <SiteFooter variant="pinned" />
    </div>
  );
}

// The site footer: Impressum, Login and the persistent motion switch. Two
// variants: fixed over the full-motion ride, in-flow at the foot of the quiet
// column. The switch is the same in both, so the choice is always reachable.
function SiteFooter({ variant }: { variant: "fixed" | "pinned" }) {
  const links = (
    <div className="flex gap-5 text-sm text-muted">
      <Link href="/impressum" className="transition-colors hover:text-ink">
        Impressum
      </Link>
      <Link href="/login" className="transition-colors hover:text-ink">
        Login
      </Link>
    </div>
  );

  // Full motion: a soft scrim over the ride, the canvas shows through. Quiet: a
  // solid bar that fully covers the fixed sun behind it, with a top border to
  // separate it from the content.
  const surface =
    variant === "pinned"
      ? "border-t border-line bg-bg"
      : "scrim";

  return (
    <footer
      className={`fixed inset-x-0 bottom-0 z-20 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 px-6 pb-5 pt-4 ${surface}`}
    >
      {links}
      <MotionToggle />
    </footer>
  );
}
