// Small deterministic helpers shared by the generator and the rails camera. The
// star system and the per-load section assignment both need the same fast PRNG
// and the same in-place shuffle, so they are defined once here.

// mulberry32: small, fast, deterministic. Same seed gives the same system, which
// is what makes "generative per reload" reproducible when we want to compare.
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Fisher-Yates, in place, drawing one number from rnd per step.
export function shuffle<T>(array: T[], rnd: () => number): void {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
}
