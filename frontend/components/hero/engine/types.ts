// Types shared between the hero React layer and the WebGL engine.

export interface HeroConfig {
  // Requested atom count, rounded up to a square compute texture by the engine.
  atomCount: number;
  // Seed for the generative star system; a fresh one per load makes every visit
  // a different system.
  seed: number;
  // A still, fully-formed frame with no camera ride for visitors who prefer
  // reduced motion.
  reducedMotion: boolean;
}

export interface EngineCallbacks {
  // Reports the active station (0..3, or -1 for none), how docked the camera is
  // (0..1), and the planet centre projected to screen pixels with its screen
  // radius, so the React layer can place the matching section text on the planet
  // and fade it in as the planet opens.
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
  dispose(): void;
}
