import Link from "next/link";
import { INTRO } from "@/components/hero/content";

// Shared dark-site chrome. The header and footer of the quiet pages, the
// recruiter views and the landing ride are the same dark surface with a brand
// wordmark and a few links. Built by hand in three places, they had begun to
// drift (one login target read "Anmelden" here and "Login" there). These
// primitives carry the structure once; the per-context differences (row width,
// surface, which links, fixed against in flow) come in as props.

// The focus ring used across the chrome and the accent text link, in one place so
// the outline never drifts between appearances.
const CHROME_FOCUS =
  "focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60";

// The accent text link (mailto or profile link). One string so the public
// impressum and the recruiter contact view stay identical.
export const ACCENT_LINK =
  `rounded-sm break-words text-accent underline decoration-accent/40 underline-offset-4 transition-colors hover:decoration-accent ${CHROME_FOCUS}`;

// The name as a link home, shared by the quiet and recruiter headers. The
// recruiter header adds the quiet-press affordance.
function BrandWordmark({ quietPress = false }: { quietPress?: boolean }) {
  return (
    <Link
      href="/"
      className={`${quietPress ? "quiet-press " : ""}rounded-sm text-sm font-medium tracking-[-0.02em] text-ink transition-colors hover:text-accent ${CHROME_FOCUS}`}
    >
      {INTRO.name}
    </Link>
  );
}

// A chrome link (Impressum, Zur Startseite, Login). Colour and size come from the
// surrounding row; the link carries only the hover and focus ring, with room for
// the few extra utilities a given spot needs.
export function ChromeLink({
  href,
  className = "",
  children,
}: {
  href: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`rounded-sm transition-colors hover:text-ink ${CHROME_FOCUS}${className ? ` ${className}` : ""}`}
    >
      {children}
    </Link>
  );
}

// The header: a brand wordmark and a right-hand slot on a row whose width and
// surface differ per context (a quiet centred bar, the recruiter's sticky
// full-width bar).
export function SiteHeader({
  outerClassName = "",
  rowClassName,
  brandQuietPress = false,
  children,
}: {
  outerClassName?: string;
  rowClassName: string;
  brandQuietPress?: boolean;
  children: React.ReactNode;
}) {
  return (
    <header className={outerClassName}>
      <div className={rowClassName}>
        <BrandWordmark quietPress={brandQuietPress} />
        {children}
      </div>
    </header>
  );
}

// The footer: a row of links (and an optional trailing control such as the motion
// switch), fixed over the ride or in flow at the foot of the quiet pages. The
// links come in as children, so each context passes the set it needs.
export function SiteFooter({
  outerClassName = "",
  rowClassName,
  children,
}: {
  outerClassName?: string;
  rowClassName: string;
  children: React.ReactNode;
}) {
  return (
    <footer className={outerClassName}>
      <div className={rowClassName}>{children}</div>
    </footer>
  );
}
