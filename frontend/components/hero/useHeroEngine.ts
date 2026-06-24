"use client";

// The hero engine lifecycle. Owns the refs and the active-station state the ride
// needs, builds (and rebuilds) the WebGL engine when the seed or the motion
// preference changes, wires the per-frame onStation callback that positions the
// visible station text, hands the generated system colours to the rest of the
// site, and disposes the engine on cleanup. Pulled verbatim out of the Hero body:
// the onStation hot-path, the build/dispose lifecycle and the [seed, reducedMotion]
// dependencies are unchanged.

import { useEffect, useRef, useState } from "react";
import type { EngineHandle } from "./engine/types";
import { systemIsCompact } from "@/lib/motion";
import { STATIONS } from "./stations";

// three touches browser-only globals, so the engine is imported lazily inside the
// effect. That keeps the page server-renderable and code-splits the heavy bundle.

// The desktop configuration: the approved 120k individual lit points.
const ATOM_COUNT = 120000;
// On a compact / coarse-pointer device the GPGPU step runs every atom every
// frame regardless of render mode, so the atom count is the honest performance
// lever for the phone. A lower count keeps the simulation light while the quiet
// sun stays dense enough to read (the sun still owns ~40% of the budget). Keyed
// to the device, not the mode, so even the deliberate full-motion option on a
// phone runs the lighter simulation. The exact value is tuned against an
// emulated budget; the real-device 60fps confirmation is Alexander's to make.
const MOBILE_ATOM_COUNT = 45000;

function randomSeed() {
  return Math.floor(Math.random() * 1_000_000);
}

export interface HeroEngine {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  sectionRefs: React.RefObject<(HTMLDivElement | null)[]>;
  // A fresh system per load, surfaced so the scroll-reset effect shares the exact
  // same dependency as the engine build.
  seed: number;
  // Active station drives which title gets the assemble animation.
  active: number;
}

export function useHeroEngine(reducedMotion: boolean): HeroEngine {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const engineRef = useRef<EngineHandle | null>(null);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const activeRef = useRef(-1);

  // A fresh system per load. Not rendered into markup, so no hydration mismatch.
  const [seed] = useState(randomSeed);
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

    // Read the device class at build time: compact devices run the lighter
    // simulation. Read here rather than via the motion hook because the count
    // tracks the hardware, not the chosen mode.
    const atomCount = systemIsCompact() ? MOBILE_ATOM_COUNT : ATOM_COUNT;

    (async () => {
      try {
        const { createWebglEngine } = await import("./engine/webglEngine");
        handle = await createWebglEngine(
          canvas,
          {
            atomCount,
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

  return { canvasRef, sectionRefs, seed, active };
}
