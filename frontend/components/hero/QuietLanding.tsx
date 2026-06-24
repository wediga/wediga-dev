import type { SkillCategory } from "@/lib/types";
import { INTRO, LANDING, accessLead } from "./content";
import { AccessButton } from "./LandingContent";
import { SkillGroup } from "./SkillGroup";
import { SiteFooter } from "./SiteFooter";

// The quiet landing. A wide two-track layout: the public content reads down a
// left-aligned column in a calm, ordinary scroll, while the living sun sits big
// on the other track and stays in view (sticky) as you read. Real DOM text
// throughout, the same teaser, toolkit and access door as the full-motion ride,
// so both appearances say the same thing. The canvas hosts the engine's quiet
// render mode (the sun alone, cursor-reactive, no camera ride).
export function QuietLanding({
  canvasRef,
  skills,
  isRecruiter,
}: {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  return (
    <div className="relative min-h-[100dvh] px-[max(28px,6vw)]">
      {/* The living sun. The screen splits in two: on wide screens the sun is
          fixed and stationary, centred in the RIGHT half (its centre at 75% of
          the width), a dominant anchor that does not move as the content scrolls.
          It is sized to stay within that right half, so it never crosses into the
          text. On narrow screens it sits in flow above the content (the full
          mobile pass is its own phase). The canvas is square so the sun stays
          round, and the engine keeps margin inside it so the cursor never clips. */}
      <div className="mx-auto mb-[2vh] flex aspect-square w-full max-w-[440px] items-center justify-center xl:fixed xl:left-3/4 xl:top-1/2 xl:z-0 xl:mx-0 xl:mb-0 xl:aspect-auto xl:h-[min(84vh,42vw)] xl:w-[min(84vh,42vw)] xl:max-w-none xl:-translate-x-1/2 xl:-translate-y-1/2">
        <canvas ref={canvasRef} className="h-full w-full" aria-hidden="true" />
      </div>

      {/* Content. The text column sits in the LEFT half, anchored to its right
          edge so it meets the centre line, with the sun centred in the right half
          beside it. The text itself is centre-aligned within that fixed column
          (centred heading, the lines overhanging evenly left and right), it is
          not pushed around in the half. An ordinary calm scroll; clears the
          pinned footer at the foot. */}
      <div className="relative z-10 pb-[16vh] pt-[4vh] xl:flex xl:w-1/2 xl:justify-end xl:pb-[20vh] xl:pr-[3vw] xl:pt-[15vh]">
        {/* Below xl the sun sits centred above the content, so the content column
            is centred under it (a readable measure, not pinned to the far left
            on a tablet). At xl the two-track takes over and these reset. */}
        <div className="mx-auto max-w-[34rem] xl:mx-0 xl:w-[34rem] xl:max-w-none xl:text-center">
        <section>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/portrait.jpg"
            alt="Alexander Wedig"
            width={64}
            height={64}
            className="mb-8 h-28 w-28 rounded-full object-cover sm:h-32 sm:w-32 xl:mx-auto"
          />
          <h1 className="text-[clamp(2.4rem,4.4vw,4rem)] font-medium leading-[1.02] tracking-[-0.02em] text-ink text-balance">
            {INTRO.name}
          </h1>
          <p className="mt-4 font-mono text-sm uppercase tracking-[0.14em] text-muted">
            {INTRO.role}
          </p>
          <p className="mt-5 max-w-[20ch] text-[clamp(1.3rem,2.1vw,1.85rem)] leading-snug text-ink sm:max-w-[34ch] xl:mx-auto">
            {INTRO.hook}
          </p>
        </section>

        {skills.length > 0 ? (
          <section className="mt-[11vh]">
            <h2 className="text-[clamp(1.8rem,3vw,2.6rem)] font-medium tracking-[-0.02em] text-ink">
              {LANDING.toolkitHeading}
            </h2>
            <div className="mt-7 space-y-6">
              {skills.map((category) => (
                <SkillGroup
                  key={category.id}
                  category={category}
                  labelClass="font-mono text-xs uppercase tracking-[0.14em] text-muted-2"
                  listClass="mt-2.5 flex flex-wrap gap-2 xl:justify-center"
                  pillClass="rounded-full bg-white/[0.06] px-4 py-1.5 font-mono text-sm text-ink"
                />
              ))}
            </div>
          </section>
        ) : null}

        <section className="mt-[11vh]">
          <h2 className="text-[clamp(1.8rem,3vw,2.6rem)] font-medium tracking-[-0.02em] text-ink">
            {LANDING.accessHeading}
          </h2>
          <p className="mt-4 max-w-[46ch] text-lg leading-relaxed text-muted xl:mx-auto">
            {accessLead(isRecruiter)}
          </p>
          <div className="mt-7">
            <AccessButton isRecruiter={isRecruiter} quiet />
          </div>
        </section>
        </div>
      </div>

      {/* Pinned to the bottom edge of the viewport, covering the sun behind it. */}
      <SiteFooter variant="pinned" />
    </div>
  );
}
