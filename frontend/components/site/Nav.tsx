import Link from "next/link";

/**
 * Fixed top bar: a mono logo with a small accent node-dot and the two public
 * links. Accent appears only on hover, the bar stays one line under 80px.
 */
export default function Nav() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 top-0 flex h-[72px] items-center justify-between px-6 sm:px-11"
      style={{ zIndex: "var(--z-nav)" }}
    >
      <Link
        href="/"
        className="flex items-center gap-[9px] font-mono text-[15px] font-medium text-ink"
      >
        <span
          className="size-2 rounded-full bg-accent"
          style={{ boxShadow: "0 0 12px 2px rgba(169,135,255,0.75)" }}
          aria-hidden="true"
        />
        wediga.dev
      </Link>
      <div className="flex items-center gap-7">
        <Link
          href="/impressum"
          className="font-mono text-[13px] text-muted transition-colors duration-200 hover:text-ink"
        >
          Impressum
        </Link>
        <Link
          href="/login"
          className="font-mono text-[13px] text-muted transition-colors duration-200 hover:text-ink"
        >
          Login
        </Link>
      </div>
    </nav>
  );
}
