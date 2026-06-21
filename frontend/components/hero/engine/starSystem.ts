// Generative star-system layout. Given a count of atoms and a seed, it builds a
// curated star system (one sun plus a handful of planets) and assigns every atom
// a home: a local offset on its body, the body's orbit parameters, a chaos start
// position and an impulse delay so the ordering reads as a wave from the centre
// outward. The output is plain typed arrays the WebGL engine uploads as textures
// or attributes without reshaping. Same seed gives the same system.

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
  // Per-atom rgb (0..1). The sun runs a warm core-to-rim ramp, each planet a
  // multi-tone body around a curated base hue. Generated per seed.
  color: Float32Array;
  // Which body each atom belongs to: -1 for the sun, otherwise the planet index
  // into meta.planets. Lets the engine open a single planet on demand.
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
  // The sun's body radius in world units. Read-only metadata; the quiet render
  // mode uses it to frame the sun, and it does not affect the full ride.
  sunRadius: number;
  planets: PlanetMeta[];
  // A representative sun tone (a mid rim sample of the warm core-to-rim ramp).
  // Read-only metadata for the UI accent; the sun's per-atom colours are
  // unchanged by this.
  sunColor: [number, number, number];
}

function clamp(x: number, lo: number, hi: number): number {
  return x < lo ? lo : x > hi ? hi : x;
}

// HSL to RGB, all inputs and outputs in 0..1 (hue is fractional turns).
function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  const hue2rgb = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  if (s === 0) return [l, l, l];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return [hue2rgb(p, q, h + 1 / 3), hue2rgb(p, q, h), hue2rgb(p, q, h - 1 / 3)];
}

// The sun owns warm orange to yellow (roughly 15 to 60), so the planet palette
// lives on the cool arc 75..350 (green, teal, blue, indigo, violet, magenta,
// rose), which keeps the sun readable. Planet hues are spread evenly across this
// arc per system and then shuffled, not picked independently, so planets stay
// distinct from one another instead of clustering into similar colours.
const PLANET_HUE_LO = 75;
const PLANET_HUE_HI = 350;

// mulberry32: small, fast, deterministic. Same seed gives the same system, which
// is what makes "generative per reload" reproducible when we want to compare.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Body {
  kind: 0 | 1; // 0 sun, 1 planet
  radius: number; // body size
  orbitRadius: number;
  orbitPhase: number;
  orbitSpeed: number;
  inclination: number;
  spinSpeed: number;
  weight: number; // share of the atom budget
  // Colour basis. The sun ignores these (it ramps by radius); each planet picks a
  // curated base hue and a small spread so the body carries several tones.
  baseHue: number; // degrees
  baseSat: number;
  baseLight: number;
  hueSpread: number; // degrees, half-width of the per-atom hue jitter
}

export function generateStarSystem(
  count: number,
  seed: number,
  minPlanets = 0,
): StarSystemData {
  const rng = mulberry32(seed);
  const rand = (lo: number, hi: number) => lo + (hi - lo) * rng();

  // Curated planet count: enough to feel like a system, never a cluttered mess,
  // but never fewer than the sections that need a planet to anchor them.
  const planetCount = Math.max(Math.round(rand(4, 9)), minPlanets);

  const bodies: Body[] = [];

  // The sun sits at the origin and carries the largest share of atoms so it
  // reads as a dense glowing core.
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

  // Planets on spaced orbits. Speed falls off with distance (loosely Keplerian),
  // so inner planets visibly circle while outer ones drift, which keeps the
  // finished system alive without looking like a spinning turntable. Each planet
  // gets a different self-spin and a curated base colour.
  const planets: PlanetMeta[] = [];
  let orbitR = sunRadius + rand(2.2, 3.0);
  const planetWeights: number[] = [];

  // Spread the planet base hues evenly across the cool arc, one per slice, then
  // shuffle so colour is not tied to orbit distance (no rainbow-by-distance).
  const hueSlot = (PLANET_HUE_HI - PLANET_HUE_LO) / planetCount;
  const planetHues: number[] = [];
  for (let p = 0; p < planetCount; p++) {
    planetHues.push(
      PLANET_HUE_LO + hueSlot * (p + 0.5) + (rng() - 0.5) * hueSlot * 0.6,
    );
  }
  for (let p = planetHues.length - 1; p > 0; p--) {
    const j = Math.floor(rng() * (p + 1));
    [planetHues[p], planetHues[j]] = [planetHues[j], planetHues[p]];
  }

  for (let p = 0; p < planetCount; p++) {
    const pradius = rand(0.45, 1.15);
    const w = pradius * pradius; // bigger planets earn more atoms
    planetWeights.push(w);

    const baseHue = planetHues[p];
    const baseSat = rand(0.4, 0.7); // curated, never neon, a touch more spread
    const baseLight = rand(0.46, 0.7);
    const hueSpread = rand(8, 16);
    const orbitSpeed =
      (rand(0.18, 0.3) / Math.sqrt(orbitR)) * (rng() > 0.5 ? 1 : -1);
    const spinSpeed = rand(0.16, 0.5); // dezent but visible once the body is coloured
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

  // Distribute the atom budget. Sun takes its fixed share, planets split the rest
  // weighted by size, with a floor so a small planet still holds enough grains to
  // be visible.
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

  const initial = new Float32Array(count * 3);
  const local = new Float32Array(count * 3);
  const orbit = new Float32Array(count * 4);
  const misc = new Float32Array(count * 4);
  const color = new Float32Array(count * 3);
  const bodyId = new Float32Array(count);

  // The impulse radiates from the centre; an atom's delay grows with how far its
  // home orbit sits from the core, so the sun forms first and the rim last.
  const maxOrbit = bodies.reduce((m, b) => Math.max(m, b.orbitRadius), 1);

  let i = 0;
  for (let b = 0; b < bodies.length; b++) {
    const body = bodies[b];
    const n = atomsPerBody[b];
    for (let k = 0; k < n && i < count; k++, i++) {
      // Local offset: a point on the body's surface with light radial jitter so
      // the shell has grain rather than a hard edge. The sun gets some interior
      // fill so it reads as a solid core, not a hollow sphere.
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
      local[i * 3 + 0] = dirX * r;
      local[i * 3 + 1] = dirY * r;
      local[i * 3 + 2] = dirZ * r;

      // -1 for the sun, otherwise the planet index (body order minus the sun).
      bodyId[i] = body.kind === 0 ? -1 : b - 1;

      // Chaos start: a wide, uneven cloud so the "before" state looks like raw
      // unordered data, not a tidy sphere.
      const cr = rand(8, 26);
      const cu = rng();
      const cv = rng();
      const ct = 2 * Math.PI * cu;
      const cp = Math.acos(2 * cv - 1);
      const csp = Math.sin(cp);
      initial[i * 3 + 0] = csp * Math.cos(ct) * cr;
      initial[i * 3 + 1] = csp * Math.sin(ct) * cr * 0.7;
      initial[i * 3 + 2] = Math.cos(cp) * cr;

      orbit[i * 4 + 0] = body.orbitRadius;
      orbit[i * 4 + 1] = body.orbitPhase;
      orbit[i * 4 + 2] = body.orbitSpeed;
      orbit[i * 4 + 3] = body.inclination;

      const radial = body.orbitRadius / maxOrbit; // 0 at core, 1 at the rim
      misc[i * 4 + 0] = radial * 0.85 + rng() * 0.15; // delay
      misc[i * 4 + 1] = body.spinSpeed;
      misc[i * 4 + 2] = body.kind;
      // Shade: the sun runs bright, planets sit dimmer, with per-atom variance so
      // the mass has depth instead of one flat tone.
      misc[i * 4 + 3] = body.kind === 0 ? rand(0.75, 1.0) : rand(0.3, 0.7);

      // Colour. The sun ramps from a near-white core to an orange rim, varied per
      // atom. Each planet carries several tones around its base hue, banded a
      // little by latitude so the self-spin reads. All bounds stay curated.
      let cr_, cg_, cb_;
      if (body.kind === 0) {
        const rn = Math.min(1, r / body.radius);
        const hue = (48 - 30 * rn + (rng() - 0.5) * 8) / 360;
        const sat = clamp(0.28 + 0.57 * rn + (rng() - 0.5) * 0.12, 0, 0.95);
        const light = clamp(0.97 - 0.42 * rn + (rng() - 0.5) * 0.1, 0.45, 1);
        [cr_, cg_, cb_] = hslToRgb(hue, sat, light);
      } else {
        const latitude = dirY; // unit sphere y, drives the banding
        const hueDeg =
          body.baseHue + (rng() - 0.5) * 2 * body.hueSpread + latitude * 5;
        const hue = ((((hueDeg % 360) + 360) % 360) / 360);
        const sat = clamp(body.baseSat + (rng() - 0.5) * 0.16, 0.2, 0.72);
        const light = clamp(
          body.baseLight + latitude * 0.1 + (rng() - 0.5) * 0.12,
          0.32,
          0.82,
        );
        [cr_, cg_, cb_] = hslToRgb(hue, sat, light);
      }
      color[i * 3 + 0] = cr_;
      color[i * 3 + 1] = cg_;
      color[i * 3 + 2] = cb_;
    }
  }

  // A representative sun tone, a mid-to-rim sample of the same warm ramp the sun
  // atoms run, so the UI accent can read the sun without touching the render.
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
