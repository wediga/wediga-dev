import {
  LegalLinks,
  SiteFooter as SharedSiteFooter,
} from "@/components/site/SiteChrome";
import { MotionToggle } from "@/components/MotionToggle";

// The site footer: the legal links and the motion switch. Fixed over the ride or in
// flow at the foot of the quiet column; the switch is the same in both.
export function SiteFooter({
  variant,
  webglFailed = false,
}: {
  variant: "fixed" | "pinned";
  webglFailed?: boolean;
}) {
  // Full motion: a scrim over the ride, the canvas shows through. Quiet: a solid
  // bar that covers the fixed sun behind it, with a top border off the content.
  // Either way it sits at the nav layer of the z-scale, not an arbitrary value.
  const surface =
    variant === "pinned"
      ? "border-t border-line bg-bg"
      : "scrim";

  return (
    <SharedSiteFooter
      outerClassName={`fixed inset-x-0 bottom-0 z-[var(--z-nav)] ${surface}`}
      rowClassName="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 px-6 pb-5 pt-4"
    >
      {/* The WebGL fallback note gets its own line above the links and switch. */}
      {webglFailed ? (
        <p className="basis-full text-center text-sm text-muted">
          Dein Browser kann die Animation gerade nicht darstellen, deshalb siehst
          du die ruhige Ansicht.
        </p>
      ) : null}
      <div className="flex gap-5 text-sm text-muted">
        <LegalLinks />
      </div>
      <MotionToggle unavailable={webglFailed} />
    </SharedSiteFooter>
  );
}
