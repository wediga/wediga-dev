"use client";

// The persistent motion switch. It overrides the OS setting and remembers the
// choice (localStorage, via setMotionChoice). Because it writes the data-motion
// attribute the CSS reveals and the hero both read, one switch governs the whole
// site. Two pills: the pressed one reflects the resolved mode, clicking the other
// stores that choice. Colours come from the tokens, never a raw hex.

import { setMotionChoice, type MotionMode } from "@/lib/motion";
import { useMotionMode } from "@/lib/useMotionMode";

const OPTIONS: { mode: MotionMode; label: string }[] = [
  { mode: "full", label: "Voll" },
  { mode: "reduced", label: "Ruhig" },
];

export function MotionToggle({
  className,
  unavailable = false,
}: {
  className?: string;
  // Set when WebGL failed: the page is quiet whatever the choice, so the switch
  // shows that and full cannot be picked.
  unavailable?: boolean;
}) {
  const choice = useMotionMode();
  const mode: MotionMode = unavailable ? "reduced" : choice;

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
              disabled={unavailable && option.mode === "full"}
              onClick={() => setMotionChoice(option.mode)}
              className={`flex min-h-[2.25rem] items-center px-4 py-[0.45rem] font-mono text-[0.72rem] uppercase tracking-[0.08em] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 pointer-coarse:min-h-[2.75rem] pointer-coarse:px-5 ${
                active
                  ? "bg-accent/15 text-accent"
                  : "text-muted enabled:hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
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
