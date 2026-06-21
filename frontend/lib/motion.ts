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
//   3. the default, full motion
//
// This module is framework-agnostic and carries no React, so the server layout
// can import the no-flash init script string from it. The React hook lives in
// useMotionMode.ts and the switch UI in components/MotionToggle.tsx.

export type MotionMode = "full" | "reduced";
// A choice is the deliberate, stored preference; null means "no choice yet", so
// the OS setting decides.
export type MotionChoice = MotionMode | null;

export const MOTION_STORAGE_KEY = "wediga:motion";
// Fired on the window when the choice changes, so every subscriber on the page
// (the switch, the hero) re-resolves in the same tick.
export const MOTION_EVENT = "wediga:motionchange";
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export function resolveMotion(
  choice: MotionChoice,
  prefersReduced: boolean,
): MotionMode {
  if (choice) return choice;
  return prefersReduced ? "reduced" : "full";
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
  applyMotionAttr(resolveMotion(null, systemPrefersReduced()));
}

// Re-resolve from the currently stored choice and apply it. Used when a choice is
// made in another tab (a storage event), so this tab's attribute catches up.
export function syncMotionFromStorage(): void {
  applyMotionAttr(resolveMotion(readStoredChoice(), systemPrefersReduced()));
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
  applyMotionAttr(resolveMotion(choice, systemPrefersReduced()));
  window.dispatchEvent(new Event(MOTION_EVENT));
}

// Runs in <head> before first paint, so the attribute is set before the page
// renders and there is no flash. Inlined as a string in the root layout. Kept
// tiny and dependency-free; it mirrors resolveMotion with the same priority.
export const MOTION_INIT_SCRIPT = `(function(){try{var k=${JSON.stringify(
  MOTION_STORAGE_KEY,
)},c=null;try{c=localStorage.getItem(k)}catch(e){}if(c!=="full"&&c!=="reduced")c=null;var p=window.matchMedia&&window.matchMedia(${JSON.stringify(
  REDUCED_MOTION_QUERY,
)}).matches;document.documentElement.setAttribute("data-motion",c?c:(p?"reduced":"full"))}catch(e){document.documentElement.setAttribute("data-motion","full")}})();`;
