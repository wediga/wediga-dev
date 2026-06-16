import { Hero } from "@/components/hero/Hero";
import { LandingContent } from "@/components/hero/LandingContent";
import { getAbout, getSkills } from "@/lib/content";

// The public landing. The about and skills are read from the BFF on the server,
// exactly as before, and handed to the Hero as a ready-rendered readable subtree.
// The Hero owns the presentation (the on-rails star-system ride, or a flat
// readable column under reduced motion); the data path is unchanged.
export default async function LandingPage() {
  const [about, skills] = await Promise.all([getAbout(), getSkills()]);

  return <Hero readable={<LandingContent about={about} skills={skills} />} />;
}
