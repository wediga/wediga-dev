import type { SkillCategory } from "@/lib/types";
import { INTRO, LANDING, accessLead } from "./content";
import { AccessButton } from "./LandingContent";
import { SkillGroup } from "./SkillGroup";
import { STATIONS } from "./stations";

// The visible station text of the full-motion ride: real DOM text positioned on
// the active planet via its projected screen coordinates, with a soft scrim
// behind for legibility. Only the active station is shown. The whole overlay is a
// visual duplicate of the readable layer, so it is aria-hidden and its controls
// are out of the tab order; mouse users still click the door. The per-frame
// position and opacity are written straight to these refs by the engine hook's
// onStation callback; active only flips a few times and drives the assemble
// animation on the matching title.
export function StationsOverlay({
  sectionRefs,
  active,
  skills,
  isRecruiter,
}: {
  sectionRefs: React.RefObject<(HTMLDivElement | null)[]>;
  active: number;
  skills: SkillCategory[];
  isRecruiter: boolean;
}) {
  const titleClass = (i: number) =>
    `text-[clamp(2rem,6vh,4.5rem)] font-medium leading-[1.05] tracking-[-0.02em] text-white ${
      active === i ? "hero-assemble" : ""
    }`;

  return (
    <div className="pointer-events-none fixed inset-0 z-10" aria-hidden="true">
      {STATIONS.map((kind, i) => (
        <div
          key={kind}
          ref={(el) => {
            sectionRefs.current[i] = el;
          }}
          style={{ opacity: 0, left: "50%", top: "50%" }}
          className="absolute w-[min(86vw,560px)] -translate-x-1/2 -translate-y-1/2 text-center transition-opacity duration-200"
        >
          {/* Scrim: a circular darkening over the whole opened planet, darkest
              at the centre and fading out before the rim, so the busy interior
              points calm down and the eye rests on the text while the lit rim
              stays visible. */}
          <div
            aria-hidden="true"
            className="absolute left-1/2 top-1/2 -z-10 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{
              background:
                "radial-gradient(circle closest-side at center, rgba(5,6,10,1) 0%, rgba(5,6,10,0.99) 48%, rgba(5,6,10,0.92) 72%, rgba(5,6,10,0.72) 90%, rgba(5,6,10,0) 100%)",
            }}
          />

          {kind === "intro" ? (
            <>
              {/* Small self-hosted portrait; the next/image optimizer is
                  needless for an 88 KB asset and flaky in dev, so a plain img
                  is cleaner. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/portrait.jpg"
                alt="Alexander Wedig"
                width={56}
                height={56}
                className="mx-auto mb-[2vh] h-[clamp(4rem,11vh,8rem)] w-[clamp(4rem,11vh,8rem)] rounded-full object-cover"
              />
              <h2 key={active === i ? `${i}-on` : `${i}-off`} className={titleClass(i)}>
                {INTRO.name}
              </h2>
              <p className="mt-[1vh] text-[clamp(0.72rem,1.5vh,1.05rem)] uppercase tracking-[0.12em] text-zinc-400">
                {INTRO.role}
              </p>
              <p className="mx-auto mt-[1.8vh] max-w-md text-[clamp(1rem,2.4vh,1.6rem)] leading-relaxed text-zinc-100">
                {INTRO.hook}
              </p>
            </>
          ) : null}

          {kind === "toolkit" ? (
            <>
              <h2 key={active === i ? `${i}-on` : `${i}-off`} className={titleClass(i)}>
                {LANDING.toolkitHeading}
              </h2>
              {skills.length > 0 ? (
                <div
                  key={active === i ? `${i}-groups-on` : `${i}-groups-off`}
                  className="hero-rise mt-[2.2vh] flex flex-col items-center gap-[1.6vh]"
                >
                  {skills.map((category) => (
                    <SkillGroup
                      key={category.id}
                      category={category}
                      labelClass="text-[clamp(0.6rem,1.2vh,0.8rem)] uppercase tracking-[0.14em] text-zinc-400"
                      listClass="mt-[0.8vh] flex flex-wrap justify-center gap-2"
                      pillClass="rounded-full bg-white/[0.06] px-3 py-1 text-[clamp(0.78rem,1.7vh,1.05rem)] text-zinc-100"
                    />
                  ))}
                </div>
              ) : null}
            </>
          ) : null}

          {kind === "access" ? (
            <>
              <h2 key={active === i ? `${i}-on` : `${i}-off`} className={titleClass(i)}>
                {LANDING.accessHeading}
              </h2>
              <p className="mx-auto mt-[1.8vh] max-w-md text-[clamp(1rem,2.4vh,1.6rem)] leading-relaxed text-zinc-100">
                {accessLead(isRecruiter)}
              </p>
              <div className="pointer-events-auto mt-[2vh] flex justify-center">
                <AccessButton isRecruiter={isRecruiter} decorative />
              </div>
            </>
          ) : null}
        </div>
      ))}
    </div>
  );
}
