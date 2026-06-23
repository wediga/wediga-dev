// Orbital lines: one fine ring per planet, traced on the exact tilted path the
// planet follows. They start invisible and fade in once forming is complete, so
// the lines read as "the order is now set". Pulled verbatim out of
// createWebglEngine, including its teardown.

import * as THREE from "three";
import type { StarSystemData } from "./starSystem";

export interface OrbitLinesHandle {
  // Drives the orbit-line fade from a forming-progress value (0..1).
  setOrbitOpacity(progress: number): void;
  dispose(): void;
}

export function buildOrbitLines(
  scene: THREE.Scene,
  data: StarSystemData,
): OrbitLinesHandle {
  const orbitGroup = new THREE.Group();
  scene.add(orbitGroup);
  const orbitLines: { mat: THREE.LineBasicMaterial; target: number }[] = [];
  const SEG = 192;
  for (const planet of data.meta.planets) {
    const pts: number[] = [];
    const ci = Math.cos(planet.inclination);
    const si = Math.sin(planet.inclination);
    for (let s = 0; s <= SEG; s++) {
      const a = (s / SEG) * Math.PI * 2;
      const bx = Math.cos(a) * planet.orbitRadius;
      const bz = Math.sin(a) * planet.orbitRadius;
      pts.push(bx, -bz * si, bz * ci); // matches the sim's orbit tilt
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    const mat = new THREE.LineBasicMaterial({
      color: new THREE.Color(planet.color[0], planet.color[1], planet.color[2]),
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    const line = new THREE.Line(g, mat);
    line.frustumCulled = false;
    orbitGroup.add(line);
    // Outer, larger orbits get a touch dimmer so the rim stays calm.
    orbitLines.push({ mat, target: 0.28 });
  }

  function setOrbitOpacity(progress: number) {
    for (const o of orbitLines) o.mat.opacity = progress * o.target;
  }

  function dispose() {
    orbitGroup.children.forEach((c) => {
      const line = c as THREE.Line;
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    });
  }

  return { setOrbitOpacity, dispose };
}
