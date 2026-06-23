// Pure per-frame maths lifted out of renderFrame: the pitch clamp and the open
// spring. No THREE, no shared state, no rng; same operations and same order as the
// inline blocks, so the rendered result is unchanged. Kept separate so the loop
// reads as wiring and this maths stays testable on its own.

// Clamp the camera pitch below MAX_PITCH so the forward vector never approaches
// vertical, the angle at which lookAt with a world-up flips the horizon. Returns
// the (possibly nudged) camera x/z and the refreshed last healthy horizontal
// direction, which the caller writes back. Only nudges in a degenerate
// near-overhead pose; at every station the pitch is ~20deg, so this never touches
// the normal framing.
export function clampPitch(
  camX: number,
  camY: number,
  camZ: number,
  lookX: number,
  lookY: number,
  lookZ: number,
  lastHx: number,
  lastHz: number,
): { x: number; z: number; lastHx: number; lastHz: number } {
  const MAX_PITCH = (72 * Math.PI) / 180;
  const minTan = Math.tan(MAX_PITCH);
  let hdx = camX - lookX;
  let hdz = camZ - lookZ;
  const vdy = camY - lookY;
  let hLen = Math.hypot(hdx, hdz);
  if (hLen > 1e-3) {
    lastHx = hdx / hLen;
    lastHz = hdz / hLen;
  }
  let x = camX;
  let z = camZ;
  const minH = Math.abs(vdy) / minTan;
  if (hLen < minH) {
    if (hLen < 1e-3) {
      hdx = lastHx;
      hdz = lastHz;
      hLen = 1;
    }
    const sc = minH / hLen;
    x = lookX + hdx * sc;
    z = lookZ + hdz * sc;
  }
  return { x, z, lastHx, lastHz };
}

// Advance the scrim/text open spring one frame toward the open target, identical
// to the atoms' spring (k=14, c=4.5), so the darkening tracks the visible planet
// form. Same operations, same order as the inline block.
export function stepOpenSpring(
  openVisual: number,
  openVel: number,
  openAmt: number,
  dt: number,
): { openVisual: number; openVel: number; openVis: number } {
  openVel += (openAmt - openVisual) * 14 * dt;
  openVel *= Math.exp(-4.5 * dt);
  openVisual += openVel * dt;
  const openVis = Math.min(1, Math.max(0, openVisual));
  return { openVisual, openVel, openVis };
}
