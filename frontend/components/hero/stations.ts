// Public landing stations, in fixed order: an intro teaser, a toolkit planet that
// carries the real skills, and the access door. Sparse on purpose: the public
// page is a teaser, the depth lives behind the recruiter login. One planet
// anchors each station, and the engine is told the count so it always has enough
// planets. The order is fixed; which planet holds which station is generative.
// Shared by the Hero shell (scroll track), the engine hook (station count) and
// the stations overlay (the per-station render).
export type StationKind = "intro" | "toolkit" | "access";

export const STATIONS: StationKind[] = ["intro", "toolkit", "access"];
