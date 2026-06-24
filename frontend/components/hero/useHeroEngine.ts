"use client";

// The hero engine lifecycle. Owns the refs and active-station state, rebuilds the
// WebGL engine when the seed or motion preference changes, wires the per-frame
// onStation callback that positions the station text, hands the generated system
// colours to the rest of the site, and disposes on cleanup.

import { useEffect, useRef, useState } from "react";
import type { EngineHandle } from "./engine/types";
import { systemIsCompact } from "@/lib/motion";
import { STATIONS } from "./stations";

// three touches browser-only globals, so the engine is imported lazily inside the
// effect, which keeps the page server-renderable and code-splits the heavy bundle.

const ATOM_COUNT = 120000;
// The GPGPU step runs every atom every frame, so on a compact device the count is
// the performance lever; this lower count holds the 60fps budget while the sun
// stays dense enough to read. Keyed to the device, not the mode, so even the
// full-motion option on a phone runs the lighter simulation.
const MOBILE_ATOM_COUNT = 45000;

function randomSeed() {
  return Math.floor(Math.random() * 1_000_000);
}

export interface HeroEngine {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  sectionRefs: React.RefObject<(HTMLDivElement | null)[]>;
  // A fresh system per load, surfaced so the scroll-reset effect shares the same
  // dependency as the engine build.
  seed: number;
  // Drives which title gets the assemble animation.
  active: number;
}

export function useHeroEngine(reducedMotion: boolean): HeroEngine {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const engineRef = useRef<EngineHandle | null>(null);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const activeRef = useRef(-1);

  // A fresh system per load. Not rendered into markup, so no hydration mismatch.
  const [seed] = useState(randomSeed);
  // Active station changes only a few times, so React state is fine; the per-frame
  // reveal is written to the DOM directly in the callback to avoid re-rendering
  // every frame.
  const [active, setActive] = useState(-1);

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
          // Box centre on the planet's projected centre, so the box tracks it as
          // it drifts.
          el.style.left = `${sx}px`;
          el.style.top = `${sy}px`;
          el.style.opacity = String(Math.min(1, docked));
          // Square keyed to the disc radius, so the scrim covers the planet and
          // fades just past its rim.
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

    // Read the device class at build time, not via the motion hook, because the
    // count tracks the hardware, not the chosen mode.
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
      // The recruiter and quiet views read this snapshot to colour their accent;
      // without it they fall back to crimson.
      try {
        sessionStorage.setItem(
          "hero:system-colors",
          JSON.stringify(handle.systemColors),
        );
      } catch {
        // sessionStorage can be unavailable (privacy mode), the accent then falls
        // back to crimson, so this is safe to ignore.
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
