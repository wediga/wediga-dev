"use client";

import {
  Children,
  isValidElement,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import ProgressDots from "./ProgressDots";

/**
 * The flight engine. Stations sit behind one another in depth and native scroll
 * drives a camera flying forward, not a classic page scroll. The key addition
 * over the prototype is scroll-snap: the scroll track is N full-viewport snap
 * sections inside a dedicated overflow scroller, so you always come to rest on
 * exactly one station and never between two. Because snap + stage live in their
 * own scroller, we read container.scrollTop (not window.scrollY) inside the rAF
 * frame and never attach a scroll listener.
 *
 * prefers-reduced-motion OR a small screen (max-width: 768px) switches to the
 * flat variant: the same station children render as normal stacked sections,
 * full opacity, no transforms, no snap, no fixed stage, no rAF. The content is
 * real in the DOM in both paths, only the presentation differs.
 */

// Depth between stations and the two fade falloffs, in px of translateZ.
const SPACING = 1700;
const FADE_BACK = 540; // incoming plane fades in slower
const FADE_FRONT = 450; // passing plane fades out faster
const POINTER_BAND = 140; // |dz| under this gets pointer-events

function clamp01(v: number) {
  return v < 0 ? 0 : v > 1 ? 1 : v;
}

export default function FlightDeck({
  children,
  labels,
  footer,
}: {
  children: ReactNode;
  labels?: string[];
  footer?: ReactNode;
}) {
  const stations = Children.toArray(children).filter(isValidElement);
  const count = stations.length;

  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const planeRefs = useRef<(HTMLDivElement | null)[]>([]);
  const rafId = useRef(0);

  // flat = reduced-motion or small screen. Resolved on the client only, so the
  // first paint matches the flat fallback and never gates content.
  const [flat, setFlat] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const motionQuery = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    );
    const sizeQuery = window.matchMedia("(max-width: 768px)");

    function resolve() {
      setFlat(motionQuery.matches || sizeQuery.matches);
    }
    resolve();
    motionQuery.addEventListener("change", resolve);
    sizeQuery.addEventListener("change", resolve);
    return () => {
      motionQuery.removeEventListener("change", resolve);
      sizeQuery.removeEventListener("change", resolve);
    };
  }, []);

  useEffect(() => {
    if (flat) return; // flat path does not run the loop
    const scroller = scrollerRef.current;
    if (!scroller) return;

    let lastActive = -1;

    function frame() {
      const el = scrollerRef.current;
      if (!el) return;
      // Progress is measured per snap section (clientHeight per station), NOT
      // against full scrollHeight. A trailing in-flow footer adds extra scroll
      // past the last snap section, so scrolling into it pushes prog above 1 and
      // fades the last station out before the footer appears. Station i is
      // centered when scrollTop == i * clientHeight.
      const ch = el.clientHeight;
      const prog =
        count > 1 && ch > 0 ? el.scrollTop / (ch * (count - 1)) : 0;

      let nearest = 0;
      let nearestDist = Infinity;

      for (let i = 0; i < count; i++) {
        const plane = planeRefs.current[i];
        if (!plane) continue;
        const station = count > 1 ? i / (count - 1) : 0;
        const delta = prog - station;
        const dz = delta * SPACING;

        const opacity =
          dz <= 0
            ? clamp01(1 + dz / FADE_BACK)
            : clamp01(1 - dz / FADE_FRONT);

        const near = Math.abs(dz) < POINTER_BAND;
        plane.style.transform = `translate(-50%, -50%) translateZ(${dz}px)`;
        plane.style.opacity = String(opacity);
        // The plane wrapper itself never takes pointer-events (see .flight-plane
        // in globals.css): it is full width and lives in the fixed stage, which is
        // a sibling of the scroller, not an ancestor. If the wrapper were
        // pointer-events:auto, a wheel over the station text would target it and
        // find no scrollable element in its DOM ancestor chain, so the page would
        // not scroll over the middle of the viewport. Keeping the wrapper inert to
        // pointer input lets the wheel fall through to the scroller, while the CSS
        // lifts only genuine interactive elements (links) back to auto so they
        // stay clickable.
        // Far planes are faded to zero but still in the fixed stage, so keep them
        // out of tab order and the a11y tree until they are near the camera.
        // inert also blocks pointer input on the lifted links of far planes, so
        // only the near station is interactive. This never gates content presence.
        plane.inert = !near;

        const adist = Math.abs(delta);
        if (adist < nearestDist) {
          nearestDist = adist;
          nearest = i;
        }
      }

      if (nearest !== lastActive) {
        lastActive = nearest;
        setActiveIndex(nearest);
      }

      rafId.current = requestAnimationFrame(frame);
    }

    rafId.current = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafId.current);
  }, [flat, count]);

  function scrollToStation(i: number) {
    const el = scrollerRef.current;
    if (!el) return;
    // One snap section is clientHeight tall, so station i sits at i * clientHeight.
    el.scrollTo({ top: i * el.clientHeight, behavior: "smooth" });
  }

  // Flat variant: same children, normal stacked sections, no transforms.
  if (flat) {
    return (
      <div className="flex flex-col">
        {stations.map((child, i) => (
          <section
            key={i}
            className="flex min-h-[80vh] items-center py-24"
          >
            {child}
          </section>
        ))}
        {footer}
      </div>
    );
  }

  // Flying variant: a dedicated snap scroller drives the fixed perspective stage.
  return (
    <>
      {/*
        Fixed perspective stage, overlays the scroller, never takes scroll.
        The station content lives here (the real, readable DOM, NOT aria-hidden),
        so screenreader, keyboard and E2E reach it regardless of flight state.
        pointer-events are off on the stage and on every plane wrapper; only the
        interactive elements opt back in (.flight-plane in globals.css), and far
        planes are inert, so a wheel over the station text falls through to the
        scroller while the near station's links stay clickable.
      */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          zIndex: "var(--z-stage)",
          perspective: "1000px",
          perspectiveOrigin: "50% 50%",
        }}
      >
        {stations.map((child, i) => (
          <div
            key={i}
            ref={(node) => {
              planeRefs.current[i] = node;
            }}
            className="flight-plane absolute left-1/2 top-1/2 w-full"
            style={{
              willChange: "transform, opacity",
              transformStyle: "preserve-3d",
            }}
          >
            {child}
          </div>
        ))}
      </div>

      {/*
        The scroll-drivers live in the same scroller as the footer, so the whole
        page is one scroll context. One full-viewport snap section per station,
        then the real footer as a final NON-snapping in-flow block. Scrolling past
        the last snap section into the footer pushes the flight progress above 1,
        which fades the last station out (see the per-section prog math) before
        the footer reaches the viewport, so the fixed stage never overlaps it.
        The footer sits above the stage so its links stay clickable.
      */}
      <div
        ref={scrollerRef}
        className="h-[100dvh] overflow-y-auto"
        style={{ scrollSnapType: "y mandatory" }}
      >
        {stations.map((_, i) => (
          <div
            key={i}
            aria-hidden="true"
            className="h-[100dvh]"
            style={{ scrollSnapAlign: "start" }}
          />
        ))}
        {footer ? (
          <div className="relative" style={{ zIndex: "var(--z-dots)" }}>
            {footer}
          </div>
        ) : null}
      </div>

      <ProgressDots
        count={count}
        activeIndex={activeIndex}
        onSelect={scrollToStation}
        labels={labels}
      />
    </>
  );
}
