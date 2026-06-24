import Link from "next/link";
import { SiteFooter as SharedSiteFooter } from "@/components/site/SiteChrome";
import { MotionToggle } from "@/components/MotionToggle";

// The site footer: Impressum, Login and the persistent motion switch. Two
// variants: fixed over the full-motion ride, in-flow at the foot of the quiet
// column. The switch is the same in both, so the choice is always reachable.
export function SiteFooter({ variant }: { variant: "fixed" | "pinned" }) {
  // Full motion: a soft scrim over the ride, the canvas shows through. Quiet: a
  // solid bar that fully covers the fixed sun behind it, with a top border to
  // separate it from the content. Either way it sits at the nav layer of the
  // semantic z-scale, never an arbitrary value.
  const surface =
    variant === "pinned"
      ? "border-t border-line bg-bg"
      : "scrim";

  return (
    <SharedSiteFooter
      outerClassName={`fixed inset-x-0 bottom-0 z-[var(--z-nav)] ${surface}`}
      rowClassName="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 px-6 pb-5 pt-4"
    >
      <div className="flex gap-5 text-sm text-muted">
        <Link href="/impressum" className="transition-colors hover:text-ink">
          Impressum
        </Link>
        <Link href="/login" className="transition-colors hover:text-ink">
          Login
        </Link>
      </div>
      <MotionToggle />
    </SharedSiteFooter>
  );
}
