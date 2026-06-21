"use client";

// The visible, persistent motion switch. It overrides the OS setting and
// remembers the choice (localStorage, via setMotionChoice), and because it writes
// the data-motion attribute that the CSS reveals and the hero both read, one
// switch governs the whole site, not just this page. Two pills mirror the mock:
// the pressed one reflects the resolved mode, clicking the other stores that
// choice. Colours come from the tokens, never a raw hex.

import { setMotionChoice, type MotionMode } from "@/lib/motion";
import { useMotionMode } from "@/lib/useMotionMode";

const OPTIONS: { mode: MotionMode; label: string }[] = [
  { mode: "full", label: "Voll" },
  { mode: "reduced", label: "Ruhig" },
];

export function MotionToggle({ className }: { className?: string }) {
  const mode = useMotionMode();

  return (
    <div
      className={`flex items-center gap-3 font-mono text-[0.72rem] uppercase tracking-[0.12em] text-muted-2 ${
        className ?? ""
      }`}
    >
      <span>Bewegung</span>
      <span
        role="group"
        aria-label="Bewegung auf der Seite"
        className="inline-flex overflow-hidden rounded-full border border-line"
      >
        {OPTIONS.map((option) => {
          const active = mode === option.mode;
          return (
            <button
              key={option.mode}
              type="button"
              aria-pressed={active}
              onClick={() => setMotionChoice(option.mode)}
              className={`flex min-h-[2.25rem] items-center px-4 py-[0.45rem] font-mono text-[0.72rem] uppercase tracking-[0.08em] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 pointer-coarse:min-h-[2.75rem] pointer-coarse:px-5 ${
                active
                  ? "bg-accent/15 text-accent"
                  : "text-muted hover:text-ink"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </span>
    </div>
  );
}
