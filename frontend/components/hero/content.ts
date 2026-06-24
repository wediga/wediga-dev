// Static intro copy for the landing, no BFF source: the name, role and hook are
// the page's own identity, edited by hand. Shared by the Intro station, the
// readable/SEO layer and the page metadata so they always read the same.
export const INTRO = {
  name: "Alexander Wedig",
  role: "Softwareentwickler aus Berlin",
  hook: "Auf dem Weg ins Machine Learning Engineering.",
} as const;

// The landing's section copy in one place so the three renderings (station
// overlay, readable/SEO layer, quiet landing) never drift apart. Their markup
// differs, but the words live here only.
export const LANDING = {
  toolkitHeading: "Toolkit",
  accessHeading: "Zugang",
} as const;

// The access lead depends on the recruiter session: a redeemed link is told the
// door is open, everyone else is pointed at the login.
export function accessLead(isRecruiter: boolean): string {
  return isRecruiter
    ? "Ihr Zugang ist freigeschaltet."
    : "Das vollständige Portfolio liegt hinter dem Login.";
}
