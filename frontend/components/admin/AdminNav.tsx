"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Client-side so it can mark the current section; carries no auth logic, the
// server layout still gates every render.
const NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/about", label: "About" },
  { href: "/admin/projects", label: "Projects" },
  { href: "/admin/skills", label: "Skills" },
  { href: "/admin/contact", label: "Contact" },
  { href: "/admin/impressum", label: "Impressum" },
  { href: "/admin/repos", label: "Repos" },
  { href: "/admin/cv", label: "CV" },
  { href: "/admin/links", label: "Links" },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap items-center gap-x-1 gap-y-1 text-sm">
      {NAV.map((item) => {
        // Overview matches only itself; the others match their subtree, so a
        // nested page highlights its section.
        const active =
          item.href === "/admin"
            ? pathname === "/admin"
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`inline-flex items-center rounded-md px-2.5 py-1.5 transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 pointer-coarse:min-h-[2.5rem] pointer-coarse:px-3 ${
              active
                ? "bg-surface text-ink"
                : "text-muted hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
