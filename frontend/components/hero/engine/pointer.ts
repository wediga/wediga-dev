// Pointer input: a camera ray through the cursor, published to the velocity
// uniforms so atoms get pushed at any depth and height.

import * as THREE from "three";

export interface PointerHandle {
  updateCursor(): void;
  dispose(): void;
}

export function buildPointer(
  canvas: HTMLCanvasElement,
  camera: THREE.PerspectiveCamera,
  vu: { [uniform: string]: THREE.IUniform },
): PointerHandle {
  const ndc = new THREE.Vector2();
  let cursorInside = false;
  const rayOrigin = new THREE.Vector3();
  const rayDir = new THREE.Vector3();
  function onPointerMove(e: PointerEvent) {
    const rect = canvas.getBoundingClientRect();
    ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    cursorInside = true;
  }
  function onPointerLeave() {
    cursorInside = false;
  }
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerleave", onPointerLeave);

  function updateCursor() {
    if (!cursorInside) {
      vu.uCursorActive.value = 0;
      return;
    }
    // Camera ray (origin + direction) instead of a flat-plane hit point, so the
    // push works at any depth and height, not just on y = 0.
    rayOrigin.copy(camera.position);
    rayDir.set(ndc.x, ndc.y, 0.5).unproject(camera).sub(rayOrigin).normalize();
    vu.uCursorOrigin.value.copy(rayOrigin);
    vu.uCursorDir.value.copy(rayDir);
    vu.uCursorActive.value = 1;
  }

  function dispose() {
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerleave", onPointerLeave);
  }

  return { updateCursor, dispose };
}
