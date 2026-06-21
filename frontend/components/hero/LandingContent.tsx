import Link from "next/link";
import type { SkillCategory } from "@/lib/types";
import { INTRO, LANDING, accessLead } from "./content";

// The real, readable landing content: an intro teaser (name, role, hook), the
// public toolkit (skills from the BFF), and the access door. It is always present
// in the DOM for screen readers, search engines and the E2E suite. The Hero
// decides where to mount it: the visible, interactive column under reduced
// motion, or the accessible SEO layer behind the canvas during the full ride.
// The full About story is intentionally NOT here; the public layer is a teaser
// plus skills, the About story finds its visible home in the recruiter views.
// GitHub/LinkedIn are also intentionally absent: the public impressum endpoint
// only exposes name and email (the impressum split), so the social links stay
// behind the login and are not surfaced on the public landing.
export function LandingContent({
  skills,
  isRecruiter,
}: {
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      {/* The page's one h1: the name, not the domain. Carries the identity for
          search engines and the document outline. */}
      <h1 className="text-4xl font-medium tracking-[-0.02em] text-ink">
        {INTRO.name}
      </h1>
      <p className="mt-2 text-sm uppercase tracking-[0.12em] text-muted">
        {INTRO.role}
      </p>
      <p className="mt-4 text-lg leading-relaxed text-ink">{INTRO.hook}</p>

      {skills.length > 0 ? (
        <section className="mt-12">
          <h2 className="text-xl font-medium tracking-[-0.02em] text-ink">
            {LANDING.toolkitHeading}
          </h2>
          <div className="mt-5 space-y-5">
            {skills.map((category) => (
              <SkillGroup key={category.id} category={category} />
            ))}
          </div>
        </section>
      ) : null}

      <section className="mt-12">
        <h2 className="text-xl font-medium tracking-[-0.02em] text-ink">
          {LANDING.accessHeading}
        </h2>
        <p className="mt-2 leading-relaxed text-ink">{accessLead(isRecruiter)}</p>
        <div className="mt-5">
          <AccessButton isRecruiter={isRecruiter} />
        </div>
      </section>
    </div>
  );
}

// One skill category: a quiet label and the skills as low-contrast tags. Tags,
// not a bulleted list, so the toolkit reads as a calm group and never as a
// data dump. Shared shape with the visible Toolkit station.
function SkillGroup({ category }: { category: SkillCategory }) {
  if (category.skills.length === 0) return null;
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.14em] text-muted">
        {category.name}
      </p>
      <ul className="mt-2 flex flex-wrap gap-2">
        {category.skills.map((skill) => (
          <li
            key={skill.id}
            className="rounded-full bg-white/[0.06] px-3 py-1 text-sm text-ink"
          >
            {skill.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

// The access door, two states. Without a recruiter session it leads to the
// login; with a valid one it goes one door further, into the portfolio. The
// server decides which state to render. `decorative` drops it from the tab
// order for the visual duplicate in the hero station. `quiet` swaps the frozen
// hero's neutral styling for the crimson accent token used by the quiet landing,
// while keeping the same href and label so the two appearances never diverge.
export function AccessButton({
  isRecruiter,
  decorative,
  quiet,
}: {
  isRecruiter: boolean;
  decorative?: boolean;
  quiet?: boolean;
}) {
  const className = quiet
    ? "quiet-press inline-block rounded-md border border-accent px-7 py-3 text-sm uppercase tracking-[0.12em] text-ink transition-colors hover:bg-accent/15 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
    : "hero-door rounded-md border border-white/25 px-6 py-2 text-sm uppercase tracking-[0.14em] text-white transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white/60";
  return (
    <Link
      href={isRecruiter ? "/portfolio" : "/login"}
      tabIndex={decorative ? -1 : undefined}
      className={className}
    >
      {isRecruiter ? "Weiter ins Portfolio" : "Anmelden"}
    </Link>
  );
}
