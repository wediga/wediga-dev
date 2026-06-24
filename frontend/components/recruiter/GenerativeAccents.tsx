"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { hslToRgb } from "@/lib/color";

// The landing stores the hero's system colours in sessionStorage; the recruiter
// views read that snapshot and paint two places: the tech dots (each cycles
// through the planet colours) and the demo/github underline (the brightest
// planet, one per system). Everything else stays the fixed crimson accent.
//
// Additive: the markup renders with the crimson fallback from CSS, and this only
// overrides the dot and underline custom properties when a snapshot exists.
// Without one (a view reached without the landing) the accent stays crimson.

type Snapshot = {
  sun: [number, number, number];
  planets: [number, number, number][];
};

// rgb (0..1) -> hsl (h 0..1, s/l 0..1).
function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return [h, s, l];
}

// Clamp a planet colour into a band legible on the dark surface: a lightness
// floor so dim planets read, a ceiling so bright ones do not blow out, and a
// saturation floor so it does not wash out to grey.
function legible([r, g, b]: [number, number, number]): string {
  const [h, s, l] = rgbToHsl(r, g, b);
  const cl = Math.min(0.82, Math.max(0.58, l));
  const cs = Math.max(0.45, s);
  const [cr, cg, cb] = hslToRgb(h, cs, cl);
  return `rgb(${Math.round(cr * 255)} ${Math.round(cg * 255)} ${Math.round(cb * 255)})`;
}

function relLuminance([r, g, b]: [number, number, number]): number {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function GenerativeAccents() {
  // The active view swaps under a persistent shell; re-run so the dots on the
  // newly rendered page get coloured.
  const pathname = usePathname();

  useEffect(() => {
    let snapshot: Snapshot | null = null;
    try {
      const raw = sessionStorage.getItem("hero:system-colors");
      if (raw) snapshot = JSON.parse(raw) as Snapshot;
    } catch {
      snapshot = null;
    }

    const planets = snapshot?.planets;
    if (!Array.isArray(planets) || planets.length === 0) return;

    const planetCss = planets.map(legible);
    // One shared underline colour per system: the brightest planet.
    const brightest = planets
      .map((c, i) => ({ i, lum: relLuminance(c) }))
      .sort((a, b) => b.lum - a.lum)[0].i;
    document.documentElement.style.setProperty(
      "--gen-underline",
      planetCss[brightest],
    );

    const dots = document.querySelectorAll<HTMLElement>("[data-gen-dot]");
    dots.forEach((el, i) => {
      el.style.setProperty("--gen-dot", planetCss[i % planetCss.length]);
    });

    return () => {
      // Back to the crimson fallback when the views unmount.
      document.documentElement.style.removeProperty("--gen-underline");
    };
  }, [pathname]);

  return null;
}
