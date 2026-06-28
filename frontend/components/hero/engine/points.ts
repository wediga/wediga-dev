// The Points object: one lit point per atom, reading the GPGPU position texture
// each frame. Geometry attributes and the ShaderMaterial are fixed at build time.

import * as THREE from "three";
import { pointsVert, pointsFrag } from "./glsl";
import type { StarSystemData } from "./starSystem";

export interface PointsHandle {
  pointsGeo: THREE.BufferGeometry;
  pointsMat: THREE.ShaderMaterial;
}

export function buildPoints(
  scene: THREE.Scene,
  data: StarSystemData,
  count: number,
  texSize: number,
  pixelRatio: number,
): PointsHandle {
  const reference = new Float32Array(count * 2);
  const sizes = new Float32Array(count);
  const shades = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    reference[i * 2 + 0] = ((i % texSize) + 0.5) / texSize;
    reference[i * 2 + 1] = (Math.floor(i / texSize) + 0.5) / texSize;
    const shade = data.misc[i * 4 + 3];
    shades[i] = shade;
    sizes[i] = 1.1 + shade * 1.4;
  }

  const pointsGeo = new THREE.BufferGeometry();
  pointsGeo.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(count * 3), 3),
  );
  pointsGeo.setAttribute("reference", new THREE.BufferAttribute(reference, 2));
  pointsGeo.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  pointsGeo.setAttribute("aShade", new THREE.BufferAttribute(shades, 1));
  pointsGeo.setAttribute("aColor", new THREE.BufferAttribute(data.color, 3));
  pointsGeo.setAttribute("aBodyId", new THREE.BufferAttribute(data.bodyId, 1));

  // Look fixed at build time: the sandbox form and body toggles are gone, this is
  // the single approved configuration.
  const pointsMat = new THREE.ShaderMaterial({
    uniforms: {
      uPositions: { value: null },
      uSizeScale: { value: 1 },
      uSoftness: { value: 0.4 },
      uIntensity: { value: 1 },
      uPixelRatio: { value: pixelRatio },
      uOpenId: { value: -1 },
      uOpen: { value: 0 },
      uDim: { value: 0 },
      uSunOnly: { value: 0 }, // quiet mode renders the sun alone; full motion at 0
    },
    vertexShader: pointsVert,
    fragmentShader: pointsFrag,
    transparent: true,
    depthWrite: true,
    depthTest: true,
  });
  const points = new THREE.Points(pointsGeo, pointsMat);
  points.frustumCulled = false;
  scene.add(points);

  return { pointsGeo, pointsMat };
}
