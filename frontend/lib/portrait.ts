import type { CSSProperties } from "react";

// The portrait comes from the backend with its crop: the point that stays in
// view, in percent of the image, and the zoom around it, in percent. The
// numbers and PORTRAIT_TYPES mirror the backend, a backend test keeps them equal.

export const FOCUS_MAX = 100;
export const ZOOM_MIN = 100;
export const ZOOM_MAX = 300;

export const PORTRAIT_TYPES = ["image/jpeg", "image/png", "image/webp"];

export const PORTRAIT_SRC = "/api/portrait";

// Zoom is stored in percent, CSS scales by a factor.
const PERCENT = 100;

export type PortraitCrop = { x: number; y: number; zoom: number };

// The crop as CSS for an image that covers its box: object-position keeps the
// focus in view, and the zoom scales the image around that same point. The
// box needs overflow hidden, so the zoomed image stays inside it.
export function cropStyle(crop: PortraitCrop): CSSProperties {
  const point = `${crop.x}% ${crop.y}%`;

  return {
    objectPosition: point,
    transform: `scale(${crop.zoom / PERCENT})`,
    transformOrigin: point,
  };
}
