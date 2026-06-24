"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// The three recruiter views in fixed order. The current one gets the crimson
// accent underline, the others stay muted until hovered.
const VIEWS = [
  { href: "/portfolio", label: "Portfolio" },
  { href: "/cv", label: "Lebenslauf" },
  { href: "/contact", label: "Kontakt" },
] as const;

export function RecruiterNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Recruiter-Ansichten" className="flex items-center gap-1">
      {VIEWS.map((view) => {
        const active = pathname === view.href;
        return (
          <Link
            key={view.href}
            href={view.href}
            aria-current={active ? "page" : undefined}
            className={`quiet-press inline-flex items-center rounded-sm px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60 pointer-coarse:min-h-[2.75rem] pointer-coarse:px-4 ${
              active
                ? "text-ink underline decoration-accent decoration-2 underline-offset-[6px]"
                : "text-muted hover:text-ink"
            }`}
          >
            {view.label}
          </Link>
        );
      })}
    </nav>
  );
}
