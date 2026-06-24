"use client";

// The two scroll-behaviour effects of the ride.

import { useEffect } from "react";

// Reset the scroll on a rebuild so the ride starts at the overview. Keyed to the
// same [seed, reducedMotion] as the engine build, so the two stay in lockstep.
export function useScrollReset(seed: number, reducedMotion: boolean) {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [seed, reducedMotion]);
}

// Scroll-snap onto each stop so the wheel locks on a station, only while the
// rails (full motion) are active.
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
