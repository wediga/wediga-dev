"use client";

// The two scroll-behaviour effects of the full-motion ride, pulled verbatim out
// of the Hero body with their exact dependencies and cleanups.

import { useEffect } from "react";

// Reset the scroll on a rebuild so the ride always starts at the overview. Keyed
// to the same [seed, reducedMotion] the engine build is, so a rebuild and the
// reset stay in lockstep.
export function useScrollReset(seed: number, reducedMotion: boolean) {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [seed, reducedMotion]);
}

// Hard scroll-snap onto each stop so the wheel locks on a station instead of
// leaving you in an in-between, only while the rails (full motion) are active.
export function useScrollSnap(reducedMotion: boolean) {
  useEffect(() => {
    if (reducedMotion) return;
    const el = document.documentElement;
    const prev = el.style.scrollSnapType;
    el.style.scrollSnapType = "y mandatory";
    return () => {
      el.style.scrollSnapType = prev;
    };
  }, [reducedMotion]);
}
