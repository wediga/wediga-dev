import type { Metadata } from "next";
import { Hero } from "@/components/hero/Hero";
import { LandingContent } from "@/components/hero/LandingContent";
import { getRecruiterSession, getSkills } from "@/lib/content";
import { INTRO } from "@/components/hero/content";

// The public landing carries only the public teaser plus the skills; the full
// About story lives behind the recruiter login, not in this SEO layer. Metadata
// is built from the intro teaser, the name as the title, the role and hook as the
// description.
export const metadata: Metadata = {
  title: INTRO.name,
  description: `${INTRO.role}. ${INTRO.hook}`,
};

// Skills are read from the BFF on the server. The recruiter session is checked
// server-side, the same live gate the recruiter layout uses, but here it only
// flips the access door between "log in" and "go to the portfolio". The gate
// itself is untouched.
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
