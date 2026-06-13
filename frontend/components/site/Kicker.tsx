import type { ReactNode } from "react";

/**
 * Small mono accent line. A single deliberate brand element, not an eyebrow
 * stamped on every section.
 */
export default function Kicker({ children }: { children: ReactNode }) {
  return (
    <span className="font-mono text-[13px] tracking-[0.12em] text-accent">
      {children}
    </span>
  );
}
