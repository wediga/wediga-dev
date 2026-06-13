import type { ReactNode } from "react";

/**
 * One station / plane in the flight. In the flying variant FlightDeck positions
 * an array of these absolutely on the perspective stage and writes transform +
 * opacity per frame via per-plane refs. In the flat variant the same children
 * render as a normal in-flow section at full opacity, no transforms. Either way
 * the children live in the real DOM and stay readable.
 *
 * The scrim is a soft radial backdrop (the .scrim utility) so the active text
 * reads over the moving starfield.
 */
export default function FlightStation({ children }: { children: ReactNode }) {
  return (
    <div className="scrim relative mx-auto w-full max-w-[760px] px-6 sm:px-11">
      {children}
    </div>
  );
}
