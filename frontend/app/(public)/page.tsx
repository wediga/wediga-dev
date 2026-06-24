import type { Metadata } from "next";
import { Hero } from "@/components/hero/Hero";
import { LandingContent } from "@/components/hero/LandingContent";
import { getRecruiterSession, getSkills } from "@/lib/content";
import { INTRO } from "@/components/hero/content";

// The public landing carries only the teaser plus skills; the About story lives
// behind the recruiter login. Metadata comes from the intro: name as title, role
// and hook as description.
export const metadata: Metadata = {
  title: INTRO.name,
  description: `${INTRO.role}. ${INTRO.hook}`,
};

// Skills are read from the BFF on the server. The recruiter session uses the same
// server-side gate as the recruiter layout, but here it only flips the access
// door between "log in" and "go to the portfolio".
export default async function LandingPage() {
  const [skills, isRecruiter] = await Promise.all([
    getSkills(),
    getRecruiterSession(),
  ]);

  return (
    <Hero
      skills={skills}
      isRecruiter={isRecruiter}
      readable={<LandingContent skills={skills} isRecruiter={isRecruiter} />}
    />
  );
}
