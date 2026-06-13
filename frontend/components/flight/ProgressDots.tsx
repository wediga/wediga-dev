/**
 * Vertical progress dots, fixed on the right. The active dot takes the accent
 * and a soft glow, the rest stay quiet. Clicking a dot asks FlightDeck to scroll
 * the container to that station. Each dot is a real button, so the flight is
 * reachable by keyboard and screenreader, not just by scrolling.
 */
export default function ProgressDots({
  count,
  activeIndex,
  onSelect,
  labels,
}: {
  count: number;
  activeIndex: number;
  onSelect: (i: number) => void;
  labels?: string[];
}) {
  return (
    <nav
      aria-label="Stations"
      className="fixed right-5 top-1/2 hidden -translate-y-1/2 flex-col gap-4 sm:right-7 md:flex"
      style={{ zIndex: "var(--z-dots)" }}
    >
      {Array.from({ length: count }, (_, i) => {
        const active = i === activeIndex;
        const label = labels?.[i] ?? `Station ${i + 1}`;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(i)}
            aria-label={`Go to ${label}`}
            aria-current={active ? "true" : undefined}
            className="group grid size-4 place-items-center"
          >
            <span
              className="size-[7px] rounded-full transition-[background-color,transform] duration-200 group-hover:scale-110"
              style={{
                backgroundColor: active
                  ? "var(--accent)"
                  : "var(--muted-2)",
                boxShadow: active
                  ? "0 0 10px 1px rgba(169,135,255,0.7)"
                  : "none",
                transitionTimingFunction: "var(--ease-out)",
              }}
            />
          </button>
        );
      })}
    </nav>
  );
}
