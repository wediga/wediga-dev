// Types shared between the hero React layer and the WebGL engine.

export interface HeroConfig {
  // Requested atom count, rounded up to a square compute texture by the engine.
  atomCount: number;
  // Seed for the generative star system; a fresh one per load varies the system.
  seed: number;
  // A still, fully-formed frame with no camera ride for visitors who prefer
  // reduced motion.
  reducedMotion: boolean;
  // Section stops the rails ride through, one planet anchors each. The generator
  // guarantees at least this many planets. Clamped to 2 upward by the engine.
  stationCount: number;
}

export interface EngineCallbacks {
  // Reports the active station (or -1 for none), how docked the camera is (0..1),
  // and the planet centre projected to screen pixels with its screen radius, so
  // the React layer can place and fade in the matching section text on the planet.
  onStation(
    stationIndex: number,
    docked: number,
    sx: number,
    sy: number,
    screenR: number,
  ): void;
}

export interface EngineHandle {
  // Atoms actually allocated (rounded up to a square texture).
  atomCount: number;
  planetCount: number;
  // The generated system's colours, the sun plus one base colour per planet, as
  // the render uses them. The landing hands these to the rest of the site for the
  // generative UI accent.
  systemColors: {
    sun: [number, number, number];
    planets: [number, number, number][];
  };
  dispose(): void;
}
