// Rails camera path maths: which planet anchors each section, the per-section
// waypoints, the scroll-to-curve mapping and the azimuthal orbit-lerp. Pure
// geometry over the generated system and the station count; it owns its own
// deterministic assignment stream and its waypoint scratch arrays. Pulled
// verbatim out of createWebglEngine; no constant, formula or draw order changed.

import * as THREE from "three";
import { mulberry32, shuffle } from "./random";
import type { StarSystemData } from "./starSystem";

// The scroll-to-curve mapping for one frame: the travel param u (0..1), the
// nearest station index, the docked dwell (0..1) and the overview approach.
export interface ScrollMap {
  u: number;
  station: number;
  docked: number;
  approach: number;
}

export interface RailsCamera {
  assignments: number[];
  planetPosAt(planetIndex: number, t: number, out: THREE.Vector3): THREE.Vector3;
  updateWaypoints(t: number): void;
  scrollProgress(): number;
  mapScroll(p: number): ScrollMap;
  orbitLerp(
    from: THREE.Vector3,
    to: THREE.Vector3,
    s: number,
    out: THREE.Vector3,
  ): void;
  camPts: THREE.Vector3[];
  lookPts: THREE.Vector3[];
  stationCam: THREE.Vector3[];
}

export function buildRailsCamera(
  data: StarSystemData,
  STATIONS: number,
  seed: number,
): RailsCamera {
  // The scroll position drives the camera along a fixed path through the section
  // planets. Progress is read in the animation frame, never via a scroll listener,
  // so native scrolling stays untouched.

  // Random per load: which planet carries each section, in fixed section order.
  // Uses its own deterministic stream so it does not disturb the generator.
  function pickAssignments(s: number, planetCount: number): number[] {
    // mulberry32 normalises the seed with >>> 0, so this matches the prior inline
    // PRNG seeded from (s ^ 0x9e3779b9) >>> 0 exactly.
    const rnd = mulberry32(s ^ 0x9e3779b9);
    const idx = Array.from({ length: planetCount }, (_, i) => i);
    shuffle(idx, rnd);
    // Always start at the outermost planet so the ride flies from OUTSIDE into the
    // system; the remaining stations are picked generatively from the rest. The
    // descending orbit-radius sort then orders the whole set outermost-first. (With
    // few stations a purely random pick could land the first stop mid-system, which
    // broke the "from outside in" feel.)
    let outer = 0;
    for (let i = 1; i < planetCount; i++) {
      if (
        data.meta.planets[i].orbitRadius > data.meta.planets[outer].orbitRadius
      ) {
        outer = i;
      }
    }
    const chosen = [
      outer,
      ...idx.filter((i) => i !== outer).slice(0, STATIONS - 1),
    ];
    chosen.sort(
      (a, b) =>
        data.meta.planets[b].orbitRadius - data.meta.planets[a].orbitRadius,
    );
    return chosen;
  }
  const assignments = pickAssignments(seed, data.meta.planets.length);

  // The scroll track is STATIONS+1 equal full-viewport snap sections (an overview
  // first, then one per station), so each leg is one snap step regardless of how far
  // apart the planets sit; the per-leg camera easing evens out the felt speed.

  const radial = new THREE.Vector3();
  function planetPosAt(planetIndex: number, t: number, out: THREE.Vector3) {
    const pl = data.meta.planets[planetIndex];
    const ang = pl.orbitPhase + t * pl.orbitSpeed;
    const bx = Math.cos(ang) * pl.orbitRadius;
    const bz = Math.sin(ang) * pl.orbitRadius;
    const si = Math.sin(pl.inclination);
    const ci = Math.cos(pl.inclination);
    return out.set(bx, -bz * si, bz * ci);
  }

  // Camera waypoints sit OUTSIDE each planet, so every station is approached from
  // outside. Between stations the path is a quadratic bezier through an outward
  // midpoint, so the curve bows gently around the bodies with an even felt speed.
  // The midpoint's outward direction is the bisector of the two stations' radial
  // directions; when the stations sit nearly opposite (the bisector collapses) it
  // bows perpendicular to the chord, so the curve always stays outside the system.
  // Seven control points: station k at index 2k, the midpoints at the odd indices.
  const camPts = Array.from(
    { length: 2 * STATIONS - 1 },
    () => new THREE.Vector3(),
  );
  const lookPts = Array.from({ length: STATIONS }, () => new THREE.Vector3());
  const stationCam = Array.from({ length: STATIONS }, () => new THREE.Vector3());
  function updateWaypoints(t: number) {
    let rim = 0;
    for (let k = 0; k < STATIONS; k++) {
      const pi = assignments[k];
      const pl = data.meta.planets[pi];
      planetPosAt(pi, t, lookPts[k]);
      radial.copy(lookPts[k]);
      if (radial.lengthSq() < 1e-4) radial.set(0, 0, 1);
      radial.normalize();
      stationCam[k]
        .copy(lookPts[k])
        .addScaledVector(radial, pl.radius * 3.4 + 6.0);
      stationCam[k].y += pl.radius * 1.2 + 2.6;
      camPts[2 * k].copy(stationCam[k]);
      rim = Math.max(rim, Math.hypot(stationCam[k].x, stationCam[k].z));
    }
    const clear = rim * 1.12 + 3;
    for (let k = 0; k < STATIONS - 1; k++) {
      const mid = camPts[2 * k + 1];
      const ax = stationCam[k].x, az = stationCam[k].z;
      const bx = stationCam[k + 1].x, bz = stationCam[k + 1].z;
      const la = Math.hypot(ax, az) || 1;
      const lb = Math.hypot(bx, bz) || 1;
      let dx = ax / la + bx / lb;
      let dz = az / la + bz / lb;
      let dl = Math.hypot(dx, dz);
      if (dl < 0.25) {
        const cx = bx - ax, cz = bz - az;
        dx = -cz;
        dz = cx;
        dl = Math.hypot(dx, dz) || 1;
      }
      mid.x = (dx / dl) * clear;
      mid.z = (dz / dl) * clear;
      mid.y = (stationCam[k].y + stationCam[k + 1].y) * 0.5 + 3;
    }
  }

  function scrollProgress(): number {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (max <= 0) return 0;
    return Math.min(1, Math.max(0, window.scrollY / max));
  }

  // Maps scroll 0..1 to a curve param with a dwell band at each station and a
  // smoothstep travel band between, so the camera eases to a gentle stop at every
  // station instead of drifting between two.
  function mapScroll(p: number): ScrollMap {
    // p maps to x in [0, STATIONS] across the equal snap sections. x = 0 is the
    // overview, x = i (i >= 1) is station i-1, where the scroll snaps and the card
    // locks. Between snaps the camera eases from one station to the next.
    const x = p * STATIONS;
    // docked: 1 only right at a station, fading sharply to 0 a short way out and flat
    // 0 across the middle of a leg, so the text and its scrim are present ONLY while
    // actually parked, not lingering faintly across the whole travel. Driven by the
    // distance in x to the nearest station (x = 1..STATIONS), so it works for the
    // lead-in and every leg alike.
    const nearest = Math.max(1, Math.round(x));
    const dxs = Math.abs(x - nearest);
    const tt = Math.min(1, Math.max(0, (dxs - 0.05) / (0.24 - 0.05)));
    const docked = 1 - tt * tt * (3 - 2 * tt);
    if (x <= 1) {
      // Lead-in: overview to the first station. approach drives the camera fly-in.
      const e = x * x * (3 - 2 * x);
      return { u: 0, station: 0, docked, approach: e };
    }
    const s = Math.min(STATIONS - 1, Math.floor(x) - 1); // lower station of this leg
    if (s >= STATIONS - 1) {
      return { u: 1, station: STATIONS - 1, docked, approach: 1 };
    }
    const lt = Math.min(1, x - (s + 1)); // 0 at station s, 1 at station s+1
    const e = lt * lt * (3 - 2 * lt);
    return {
      u: (s + e) / (STATIONS - 1),
      station: e < 0.5 ? s : s + 1,
      docked,
      approach: 1,
    };
  }

  // Interpolate between two world points as an orbit around the sun: the azimuth
  // takes the shorter way (left or right), the radius and height lerp straight. The
  // camera therefore always travels around the SIDE of the system, never across or
  // over the top, no matter where start and end sit. Used both for station-to-station
  // travel and for the overview-to-first-station fly-in.
  function orbitLerp(
    from: THREE.Vector3,
    to: THREE.Vector3,
    s: number,
    out: THREE.Vector3,
  ) {
    const aAng = Math.atan2(from.z, from.x);
    let dAng = Math.atan2(to.z, to.x) - aAng;
    while (dAng > Math.PI) dAng -= 2 * Math.PI;
    while (dAng < -Math.PI) dAng += 2 * Math.PI;
    const ang = aAng + dAng * s;
    const aR = Math.hypot(from.x, from.z);
    const r = aR + (Math.hypot(to.x, to.z) - aR) * s;
    out.set(Math.cos(ang) * r, from.y + (to.y - from.y) * s, Math.sin(ang) * r);
  }

  return {
    assignments,
    planetPosAt,
    updateWaypoints,
    scrollProgress,
    mapScroll,
    orbitLerp,
    camPts,
    lookPts,
    stationCam,
  };
}
