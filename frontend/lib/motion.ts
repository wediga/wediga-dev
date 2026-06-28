// Site-wide motion mode. Reduced still keeps the cursor-reactive sun, it only
// drops the scroll-driven camera ride and the page reveals. The data-motion
// attribute on <html> is the single source of truth, read by both the CSS
// reveals and the hero, resolved with this priority (highest first):
//   1. a stored choice (the on-page switch)
//   2. the OS prefers-reduced-motion setting
//   3. the device default: compact (phone, small tablet, coarse pointer) starts
//      quiet, everything else starts full
// Rung 3 exists because the camera ride is built for desktop landscape: in
// portrait the system sits small and off-centre, the per-frame station text
// does not land, and 120k simulated atoms risk choking a phone, so a compact
// device starts quiet unless the visitor switches to full (rung 1 still wins).
// No React here, so the server layout can import the no-flash init string.

export type MotionMode = "full" | "reduced";
// null means no stored choice yet, so the OS setting and device default decide.
export type MotionChoice = MotionMode | null;

export const MOTION_STORAGE_KEY = "wediga:motion";
// Fired on the window when the choice changes, so every subscriber (the switch,
// the hero) re-resolves in the same tick.
export const MOTION_EVENT = "wediga:motionchange";
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
// Compact: phone or small tablet by width, or any coarse pointer. The 1024px
// width matches the layouts' small/large break, and the coarse-pointer arm
// catches touch tablets in landscape that the width bound alone would miss.
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
    // localStorage can be unavailable (privacy mode), fall back to no choice.
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

// Re-resolve from the current OS setting (no-op when a choice is stored) and
// apply it. The live media-query subscription uses this so the site follows an
// OS change unless a stored choice overrides it.
export function syncMotionFromSystem(): void {
  if (readStoredChoice()) return;
  applyMotionAttr(
    resolveMotion(null, systemPrefersReduced(), systemIsCompact()),
  );
}

// Re-resolve from the stored choice and apply it. Used when another tab changes
// the choice (a storage event), so this tab's attribute catches up.
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
    // A failed write only loses persistence across reloads, the attribute is
    // still applied for this session, so the switch still works.
  }
  applyMotionAttr(
    resolveMotion(choice, systemPrefersReduced(), systemIsCompact()),
  );
  window.dispatchEvent(new Event(MOTION_EVENT));
}

// Runs in <head> before first paint so the attribute is set before render, no
// flash. Inlined as a string in the root layout, so it stays tiny and
// dependency-free and mirrors resolveMotion's priority: stored choice, then
// prefers-reduced-motion, then the compact-device default.
export const MOTION_INIT_SCRIPT = `(function(){try{var k=${JSON.stringify(
  MOTION_STORAGE_KEY,
)},c=null;try{c=localStorage.getItem(k)}catch(e){}if(c!=="full"&&c!=="reduced")c=null;var mm=window.matchMedia,p=mm&&mm(${JSON.stringify(
  REDUCED_MOTION_QUERY,
)}).matches,q=mm&&mm(${JSON.stringify(
  COMPACT_MOTION_QUERY,
)}).matches;document.documentElement.setAttribute("data-motion",c?c:((p||q)?"reduced":"full"))}catch(e){document.documentElement.setAttribute("data-motion","full")}})();`;
