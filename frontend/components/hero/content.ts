// Static intro copy for the landing. There is no BFF source for this: the name,
// role and hook are the page's own identity, and the hook is meant to be easy to
// change by hand. Shared by the visible Intro station and the readable/SEO layer
// so both always read the same, and by the page metadata.
export const INTRO = {
  name: "Alexander Wedig",
  role: "Softwareentwickler aus Berlin",
  hook: "Auf dem Weg ins Machine Learning Engineering.",
} as const;

// The public landing's section copy, in one place so the three renderings (the
// full-motion station overlay, the readable/SEO layer, and the quiet landing)
// can never drift apart. The markup of those three legitimately differs (text
// tracked onto planets, a hidden readable column, a quiet two-track layout), but
// the words live here only.
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
