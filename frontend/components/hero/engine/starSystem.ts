// Generative star-system layout. From a count of atoms and a seed it builds one
// sun plus a handful of planets and gives every atom a home: a local offset on
// its body, the body's orbit parameters, a chaos start position and an impulse
// delay so the ordering reads as a wave from the centre out. Output is typed
// arrays the engine uploads as textures or attributes. Same seed, same system.

import { hslToRgb } from "@/lib/color";
import { mulberry32, shuffle } from "./random";

export interface StarSystemData {
  count: number;
  // Chaos start position, xyz per atom.
  initial: Float32Array;
  // Offset of the atom relative to its body centre, xyz per atom.
  local: Float32Array;
  // Body orbit: radius, phase, angular speed, inclination, per atom.
  orbit: Float32Array;
  // radius, phase, speed, inclination packed as 4 floats per atom.
  misc: Float32Array;
  // delay, spinSpeed, kind (0 = sun, 1 = planet), shade (0..1), per atom.
  // Per-atom rgb (0..1).
  color: Float32Array;
  // Body each atom belongs to: -1 sun, else the planet index into meta.planets.
  // Lets the engine open a single planet on demand.
  bodyId: Float32Array;
  meta: StarSystemMeta;
}

export interface PlanetMeta {
  orbitRadius: number;
  orbitPhase: number;
  inclination: number;
  orbitSpeed: number;
  spinSpeed: number;
  radius: number;
  color: [number, number, number]; // base colour, for the orbit line
}

export interface StarSystemMeta {
  seed: number;
  planetCount: number;
  sunAtoms: number;
  // Sun body radius in world units; quiet mode uses it to frame the sun.
  sunRadius: number;
  planets: PlanetMeta[];
  // A representative sun tone (mid-rim sample of the warm ramp) for the UI accent.
  sunColor: [number, number, number];
}

function clamp(x: number, lo: number, hi: number): number {
  return x < lo ? lo : x > hi ? hi : x;
}

// The sun owns warm orange to yellow (~15..60), so the planet palette lives on
// the cool arc 75..350, which keeps the sun readable.
const PLANET_HUE_LO = 75;
const PLANET_HUE_HI = 350;

interface Body {
  kind: 0 | 1; // 0 sun, 1 planet
  radius: number; // body size
  orbitRadius: number;
  orbitPhase: number;
  orbitSpeed: number;
  inclination: number;
  spinSpeed: number;
  weight: number; // share of the atom budget
  // Colour basis. The sun ignores these (it ramps by radius); planets carry a base
  // hue plus a spread.
  baseHue: number; // degrees
  baseSat: number;
  baseLight: number;
  hueSpread: number; // degrees, half-width of the per-atom hue jitter
}

// Sun atom colour: near-white core ramping to an orange rim. rn is the normalised
// radius (0 core, 1 rim).
function sunAtomColor(
  rn: number,
  rng: () => number,
): [number, number, number] {
  const hue = (48 - 30 * rn + (rng() - 0.5) * 8) / 360;
  const sat = clamp(0.28 + 0.57 * rn + (rng() - 0.5) * 0.12, 0, 0.95);
  const light = clamp(0.97 - 0.42 * rn + (rng() - 0.5) * 0.1, 0.45, 1);
  return hslToRgb(hue, sat, light);
}

// Planet atom colour: tones around the body's base hue, banded by latitude so the
// self-spin reads.
function planetAtomColor(
  body: Body,
  latitude: number,
  rng: () => number,
): [number, number, number] {
  const hueDeg =
    body.baseHue + (rng() - 0.5) * 2 * body.hueSpread + latitude * 5;
  const hue = ((((hueDeg % 360) + 360) % 360) / 360);
  const sat = clamp(body.baseSat + (rng() - 0.5) * 0.16, 0.2, 0.72);
  const light = clamp(
    body.baseLight + latitude * 0.1 + (rng() - 0.5) * 0.12,
    0.32,
    0.82,
  );
  return hslToRgb(hue, sat, light);
}

interface AtomArrays {
  initial: Float32Array;
  local: Float32Array;
  orbit: Float32Array;
  misc: Float32Array;
  color: Float32Array;
  bodyId: Float32Array;
}

// Fill every slot for atom i on its body (bodyIndex is its position in the bodies
// array, the sun is 0). The rng draw order (u, v, r, chaos r, cu, cv, delay,
// shade, then the colour helper) is load-bearing for reproducibility per seed.
function fillAtom(
  arr: AtomArrays,
  i: number,
  body: Body,
  bodyIndex: number,
  maxOrbit: number,
  rng: () => number,
  rand: (lo: number, hi: number) => number,
): void {
  // Local offset: a surface point with radial jitter so the shell has grain. The
  // sun fills its interior (shellLo 0.35) so it reads as a solid core.
  const u = rng();
  const v = rng();
  const theta = 2 * Math.PI * u;
  const phi = Math.acos(2 * v - 1);
  const sinPhi = Math.sin(phi);
  const dirX = sinPhi * Math.cos(theta);
  const dirY = sinPhi * Math.sin(theta);
  const dirZ = Math.cos(phi);
  const shellLo = body.kind === 0 ? 0.35 : 0.9;
  const r = body.radius * rand(shellLo, 1.0);
  arr.local[i * 3 + 0] = dirX * r;
  arr.local[i * 3 + 1] = dirY * r;
  arr.local[i * 3 + 2] = dirZ * r;

  // -1 for the sun, otherwise the planet index (body order minus the sun).
  arr.bodyId[i] = body.kind === 0 ? -1 : bodyIndex - 1;

  // Chaos start: a wide uneven cloud so the before-state reads as raw unordered
  // data, not a tidy sphere.
  const cr = rand(8, 26);
  const cu = rng();
  const cv = rng();
  const ct = 2 * Math.PI * cu;
  const cp = Math.acos(2 * cv - 1);
  const csp = Math.sin(cp);
  arr.initial[i * 3 + 0] = csp * Math.cos(ct) * cr;
  arr.initial[i * 3 + 1] = csp * Math.sin(ct) * cr * 0.7;
  arr.initial[i * 3 + 2] = Math.cos(cp) * cr;

  arr.orbit[i * 4 + 0] = body.orbitRadius;
  arr.orbit[i * 4 + 1] = body.orbitPhase;
  arr.orbit[i * 4 + 2] = body.orbitSpeed;
  arr.orbit[i * 4 + 3] = body.inclination;

  const radial = body.orbitRadius / maxOrbit; // 0 at core, 1 at the rim
  arr.misc[i * 4 + 0] = radial * 0.85 + rng() * 0.15; // delay
  arr.misc[i * 4 + 1] = body.spinSpeed;
  arr.misc[i * 4 + 2] = body.kind;
  // Shade: sun bright, planets dimmer, with per-atom variance for depth.
  arr.misc[i * 4 + 3] = body.kind === 0 ? rand(0.75, 1.0) : rand(0.3, 0.7);

  // Colour: latitude is the unit-sphere y, so banding by it makes the self-spin
  // read. Maths in the helpers.
  const [cr_, cg_, cb_] =
    body.kind === 0
      ? sunAtomColor(Math.min(1, r / body.radius), rng)
      : planetAtomColor(body, dirY, rng);
  arr.color[i * 3 + 0] = cr_;
  arr.color[i * 3 + 1] = cg_;
  arr.color[i * 3 + 2] = cb_;
}

// The planned layout, including the live rng so the fill loop continues the same
// stream.
interface StarSystemPlan {
  rng: () => number;
  bodies: Body[];
  planets: PlanetMeta[];
  atomsPerBody: number[];
  planetCount: number;
  sunRadius: number;
}

// Plan the bodies and distribute the atom budget: the sun at the origin plus
// planets on spaced orbits, then the per-body atom counts. Every layout rng draw
// happens here, in order, before any atom is filled.
function planStarSystem(
  count: number,
  seed: number,
  minPlanets: number,
): StarSystemPlan {
  const rng = mulberry32(seed);
  const rand = (lo: number, hi: number) => lo + (hi - lo) * rng();

  // Never fewer planets than the sections that need one to anchor them.
  const planetCount = Math.max(Math.round(rand(4, 9)), minPlanets);

  const bodies: Body[] = [];

  // The sun carries the largest atom share so it reads as a dense core.
  const sunRadius = rand(2.4, 3.2);
  bodies.push({
    kind: 0,
    radius: sunRadius,
    orbitRadius: 0,
    orbitPhase: 0,
    orbitSpeed: rand(0.015, 0.03),
    inclination: 0,
    spinSpeed: rand(0.04, 0.08),
    weight: rand(0.36, 0.46),
    baseHue: 0,
    baseSat: 0,
    baseLight: 0,
    hueSpread: 0,
  });

  // Speed falls off with distance (loosely Keplerian), so inner planets visibly
  // circle while outer ones drift, not a uniform turntable.
  const planets: PlanetMeta[] = [];
  let orbitR = sunRadius + rand(2.2, 3.0);
  const planetWeights: number[] = [];

  // Even hues across the cool arc, one per slice, then shuffle so colour is not
  // tied to orbit distance (no rainbow-by-distance).
  const hueSlot = (PLANET_HUE_HI - PLANET_HUE_LO) / planetCount;
  const planetHues: number[] = [];
  for (let p = 0; p < planetCount; p++) {
    planetHues.push(
      PLANET_HUE_LO + hueSlot * (p + 0.5) + (rng() - 0.5) * hueSlot * 0.6,
    );
  }
  shuffle(planetHues, rng);

  for (let p = 0; p < planetCount; p++) {
    const pradius = rand(0.45, 1.15);
    const w = pradius * pradius; // bigger planets earn more atoms
    planetWeights.push(w);

    const baseHue = planetHues[p];
    const baseSat = rand(0.4, 0.7); // never neon
    const baseLight = rand(0.46, 0.7);
    const hueSpread = rand(8, 16);
    const orbitSpeed =
      (rand(0.18, 0.3) / Math.sqrt(orbitR)) * (rng() > 0.5 ? 1 : -1);
    const spinSpeed = rand(0.16, 0.5); // subtle but visible once the body is coloured
    const inclination = rand(-0.22, 0.22);
    const orbitPhase = rand(0, Math.PI * 2);

    bodies.push({
      kind: 1,
      radius: pradius,
      orbitRadius: orbitR,
      orbitPhase,
      orbitSpeed,
      inclination,
      spinSpeed,
      weight: 0,
      baseHue,
      baseSat,
      baseLight,
      hueSpread,
    });
    planets.push({
      orbitRadius: orbitR,
      orbitPhase,
      inclination,
      orbitSpeed,
      spinSpeed,
      radius: pradius,
      color: hslToRgb(baseHue / 360, baseSat, baseLight),
    });
    orbitR += rand(2.2, 3.2) + pradius;
  }

  // Sun takes its fixed share, planets split the rest by size, with a floor so a
  // small planet still holds enough grains to be visible.
  const sunShare = bodies[0].weight;
  const sunAtoms = Math.max(1, Math.round(count * sunShare));
  const planetBudget = count - sunAtoms;
  const weightSum = planetWeights.reduce((a, b) => a + b, 0) || 1;

  const atomsPerBody: number[] = new Array(bodies.length).fill(0);
  atomsPerBody[0] = sunAtoms;
  let assigned = sunAtoms;
  for (let p = 0; p < planetCount; p++) {
    const floor = Math.min(220, Math.floor(planetBudget / (planetCount * 3)));
    const share = Math.round((planetWeights[p] / weightSum) * planetBudget);
    const n = Math.max(floor, share);
    atomsPerBody[p + 1] = n;
    assigned += n;
  }
  // Reconcile rounding drift onto the sun.
  atomsPerBody[0] += count - assigned;
  if (atomsPerBody[0] < 0) atomsPerBody[0] = 0;

  return { rng, bodies, planets, atomsPerBody, planetCount, sunRadius };
}

export function generateStarSystem(
  count: number,
  seed: number,
  minPlanets = 0,
): StarSystemData {
  const { rng, bodies, planets, atomsPerBody, planetCount, sunRadius } =
    planStarSystem(count, seed, minPlanets);
  const rand = (lo: number, hi: number) => lo + (hi - lo) * rng();

  const initial = new Float32Array(count * 3);
  const local = new Float32Array(count * 3);
  const orbit = new Float32Array(count * 4);
  const misc = new Float32Array(count * 4);
  const color = new Float32Array(count * 3);
  const bodyId = new Float32Array(count);

  // Delay grows with orbit distance, so the sun forms first and the rim last.
  const maxOrbit = bodies.reduce((m, b) => Math.max(m, b.orbitRadius), 1);

  const arr: AtomArrays = { initial, local, orbit, misc, color, bodyId };
  let i = 0;
  for (let b = 0; b < bodies.length; b++) {
    const body = bodies[b];
    const n = atomsPerBody[b];
    for (let k = 0; k < n && i < count; k++, i++) {
      fillAtom(arr, i, body, b, maxOrbit, rng, rand);
    }
  }

  // A representative sun tone, a mid-to-rim sample of the same warm ramp the sun
  // atoms run, for the UI accent without touching the render.
  const sunRn = 0.75;
  const sunColor = hslToRgb(
    (48 - 30 * sunRn) / 360,
    clamp(0.28 + 0.57 * sunRn, 0, 0.95),
    clamp(0.97 - 0.42 * sunRn, 0.45, 1),
  );

  return {
    count,
    initial,
    local,
    orbit,
    misc,
    color,
    bodyId,
    meta: {
      seed,
      planetCount,
      sunAtoms: atomsPerBody[0],
      sunRadius,
      planets,
      sunColor,
    },
  };
}
