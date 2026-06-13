import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Restrained text link. A fine bottom border in --line that turns to the accent
 * on hover, never a button-badge.
 */
export default function TextLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className="border-b border-line pb-1 font-mono text-[13px] text-muted transition-colors duration-200 hover:border-accent hover:text-ink"
    >
      {children}
    </Link>
  );
}
