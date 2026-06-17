// Static intro copy for the landing. There is no BFF source for this: the name,
// role and hook are the page's own identity, and the hook is meant to be easy to
// change by hand. Shared by the visible Intro station and the readable/SEO layer
// so both always read the same, and by the page metadata.
export const INTRO = {
  name: "Alexander Wedig",
  role: "Softwareentwickler aus Berlin",
  hook: "Auf dem Weg ins Machine Learning Engineering.",
} as const;
