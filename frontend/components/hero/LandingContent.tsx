import Link from "next/link";
import type { SkillCategory } from "@/lib/types";
import { INTRO, LANDING, accessLead } from "./content";
import { SkillGroup } from "./SkillGroup";

// The readable landing content: intro teaser, public toolkit (BFF skills), and
// the access door. Always in the DOM for screen readers, search engines and the
// E2E suite. The Hero mounts it as the visible column under reduced motion, or as
// the SEO layer behind the canvas during the ride. No About story and no
// GitHub/LinkedIn here: the public impressum exposes only name and email, so the
// story and the social links stay behind the login.
export function LandingContent({
  skills,
  isRecruiter,
}: {
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      {/* The page's one h1: the name, not the domain, carrying the identity for
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
              <SkillGroup
                key={category.id}
                category={category}
                labelClass="text-xs uppercase tracking-[0.14em] text-muted"
                listClass="mt-2 flex flex-wrap gap-2"
                pillClass="rounded-full bg-white/[0.06] px-3 py-1 text-sm text-ink"
              />
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

// The access door. A redeemed recruiter session gets the button into the
// portfolio; everyone else gets a plain note pointing at the public impressum
// instead of a dead-end admin login, until the request flow (Backlog point 1)
// replaces it. `decorative` drops the interactive element from the tab order for
// the visual duplicate in the hero station. `quiet` swaps the frozen hero's
// neutral styling for the crimson accent of the quiet landing, so the
// appearances never diverge.
export function AccessButton({
  isRecruiter,
  decorative,
  quiet,
}: {
  isRecruiter: boolean;
  decorative?: boolean;
  quiet?: boolean;
}) {
  const tabIndex = decorative ? -1 : undefined;

  if (isRecruiter) {
    const className = quiet
      ? "quiet-press inline-block rounded-md border border-accent px-7 py-3 text-sm uppercase tracking-[0.12em] text-ink transition-colors hover:bg-accent/15 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
      : "hero-door rounded-md border border-white/25 px-6 py-2 text-sm uppercase tracking-[0.14em] text-white transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white/60";
    return (
      <Link href="/portfolio" tabIndex={tabIndex} className={className}>
        Weiter ins Portfolio
      </Link>
    );
  }

  const linkClass = quiet
    ? "text-accent underline-offset-4 transition-colors hover:text-ink"
    : "text-white underline underline-offset-4 transition-colors hover:text-white/80";
  return (
    <p className={quiet ? "text-base text-muted" : "text-sm text-muted"}>
      Kontakt über das{" "}
      <Link href="/impressum" tabIndex={tabIndex} className={linkClass}>
        Impressum
      </Link>
      .
    </p>
  );
}
