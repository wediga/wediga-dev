// Public landing stations in fixed order: intro teaser, toolkit planet (the real
// skills), access door. Sparse on purpose, the depth lives behind the recruiter
// login. One planet anchors each, and the engine gets the count so it has enough
// planets; which planet holds which station is generative. Shared by the Hero
// shell (scroll track), the engine hook (count) and the overlay (per-station
// render).
export type StationKind = "intro" | "toolkit" | "access";

export const STATIONS: StationKind[] = ["intro", "toolkit", "access"];
