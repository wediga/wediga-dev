// The site-wide motion mode. Reduced motion here does not mean "no motion": it
// drops the disorienting scroll-driven camera ride and the small page reveals,
// but keeps a living, cursor-reactive sun. The mode is resolved with a clear
// priority and written to a single source of truth, the data-motion attribute on
// <html>, which both the CSS reveals and the hero read, so one switch governs the
// whole site rather than only the OS media query.
//
// Priority, highest first:
//   1. a deliberate, stored choice (the on-page switch)
//   2. the OS setting, prefers-reduced-motion
//   3. the device default: compact (phone / small tablet / coarse pointer) gets
//      the quiet mode, everything else gets full motion
//
// The third rung is the H7 mobile rule. The scroll-driven camera ride is built
// for desktop landscape: in portrait the system sits small and off-centre, the
// per-frame station text does not land, and 120k simulated atoms are a real
// performance risk on a phone. The quiet sun-anchored landing is the better
// default there, so on a compact / coarse-pointer device the page starts quiet
// unless the visitor deliberately switches to full motion (the switch still
// wins, rung 1). Desktop is untouched: no stored choice and no reduced-motion
// preference still resolves to full.
//
// This module is framework-agnostic and carries no React, so the server layout
// can import the no-flash init script string from it. The React hook lives in
// useMotionMode.ts and the switch UI in components/MotionToggle.tsx.

export type MotionMode = "full" | "reduced";
// A choice is the deliberate, stored preference; null means "no choice yet", so
// the OS setting and the device default decide.
export type MotionChoice = MotionMode | null;

export const MOTION_STORAGE_KEY = "wediga:motion";
// Fired on the window when the choice changes, so every subscriber on the page
// (the switch, the hero) re-resolves in the same tick.
export const MOTION_EVENT = "wediga:motionchange";
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
// Compact: a phone or small tablet by width, or any coarse-pointer (touch)
// device. Either is enough to make the quiet mode the better default. The width
// bound sits at the same 1024px the layouts already treat as the small/large
// break, and the coarse-pointer arm catches touch tablets in landscape that the
// width bound alone would miss.
export const COMPACT_MOTION_QUERY = "(max-width: 1024px), (pointer: coarse)";

export function resolveMotion(
  choice: MotionChoice,
  prefersReduced: boolean,
  compact: boolean,
): MotionMode {
  if (choice) return choice;
  if (prefersReduced) return "reduced";
  return compact ? "reduced" : "full";
}

export function readStoredChoice(): MotionChoice {
  try {
    const value = localStorage.getItem(MOTION_STORAGE_KEY);
    return value === "full" || value === "reduced" ? value : null;
  } catch {
    // localStorage can be unavailable (privacy mode); fall back to no choice.
    return null;
  }
}

export function systemPrefersReduced(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia(REDUCED_MOTION_QUERY).matches
  );
}

export function systemIsCompact(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia(COMPACT_MOTION_QUERY).matches
  );
}

export function readMotionMode(): MotionMode {
  const attr = document.documentElement.dataset.motion;
  return attr === "reduced" ? "reduced" : "full";
}

function applyMotionAttr(mode: MotionMode): void {
  document.documentElement.dataset.motion = mode;
}

// Re-resolve the mode from the current OS setting when there is no stored choice,
// and apply it to the attribute. Used by the live media-query subscription so the
// site follows an OS change unless a deliberate choice overrides it.
export function syncMotionFromSystem(): void {
  if (readStoredChoice()) return;
  applyMotionAttr(
    resolveMotion(null, systemPrefersReduced(), systemIsCompact()),
  );
}

// Re-resolve from the currently stored choice and apply it. Used when a choice is
// made in another tab (a storage event), so this tab's attribute catches up.
export function syncMotionFromStorage(): void {
  applyMotionAttr(
    resolveMotion(readStoredChoice(), systemPrefersReduced(), systemIsCompact()),
  );
}

// Persist a deliberate choice, apply it immediately, and notify subscribers.
export function setMotionChoice(choice: MotionChoice): void {
  try {
    if (choice) localStorage.setItem(MOTION_STORAGE_KEY, choice);
    else localStorage.removeItem(MOTION_STORAGE_KEY);
  } catch {
    // A failed write only means the choice will not persist across reloads; the
    // attribute is still applied for this session, so the switch still works.
  }
  applyMotionAttr(
    resolveMotion(choice, systemPrefersReduced(), systemIsCompact()),
  );
  window.dispatchEvent(new Event(MOTION_EVENT));
}

// Runs in <head> before first paint, so the attribute is set before the page
// renders and there is no flash. Inlined as a string in the root layout. Kept
// tiny and dependency-free; it mirrors resolveMotion with the same priority:
// stored choice, then prefers-reduced-motion, then the compact-device default.
export const MOTION_INIT_SCRIPT = `(function(){try{var k=${JSON.stringify(
  MOTION_STORAGE_KEY,
)},c=null;try{c=localStorage.getItem(k)}catch(e){}if(c!=="full"&&c!=="reduced")c=null;var mm=window.matchMedia,p=mm&&mm(${JSON.stringify(
  REDUCED_MOTION_QUERY,
)}).matches,q=mm&&mm(${JSON.stringify(
  COMPACT_MOTION_QUERY,
)}).matches;document.documentElement.setAttribute("data-motion",c?c:((p||q)?"reduced":"full"))}catch(e){document.documentElement.setAttribute("data-motion","full")}})();`;
