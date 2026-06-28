// GPGPU setup: the static per-atom data textures and the GPUComputationRenderer
// that runs the atom simulation as ping-pong float textures.

import * as THREE from "three";
import { GPUComputationRenderer } from "three/examples/jsm/misc/GPUComputationRenderer.js";
import { velocityFrag, positionFrag } from "./glsl";
import type { StarSystemData } from "./starSystem";

type GpuVariable = ReturnType<GPUComputationRenderer["addVariable"]>;

export interface GpgpuHandle {
  gpu: GPUComputationRenderer;
  posVar: GpuVariable;
  // Velocity material uniforms, the engine's per-frame control surface.
  vu: { [uniform: string]: THREE.IUniform };
  localTex: THREE.DataTexture;
  orbitTex: THREE.DataTexture;
  miscTex: THREE.DataTexture;
}

export function buildGpgpu(
  renderer: THREE.WebGLRenderer,
  texSize: number,
  count: number,
  data: StarSystemData,
): GpgpuHandle {
  // --- static per-atom data textures -------------------------------------
  const localRGBA = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) {
    localRGBA[i * 4 + 0] = data.local[i * 3 + 0];
    localRGBA[i * 4 + 1] = data.local[i * 3 + 1];
    localRGBA[i * 4 + 2] = data.local[i * 3 + 2];
    localRGBA[i * 4 + 3] = data.bodyId[i]; // which planet (for the open effect)
  }
  const dataTex = (arr: Float32Array) => {
    const t = new THREE.DataTexture(
      arr,
      texSize,
      texSize,
      THREE.RGBAFormat,
      THREE.FloatType,
    );
    t.needsUpdate = true;
    return t;
  };
  const localTex = dataTex(localRGBA);
  const orbitTex = dataTex(data.orbit);
  const miscTex = dataTex(data.misc);

  // --- GPGPU setup --------------------------------------------------------
  const gpu = new GPUComputationRenderer(texSize, texSize, renderer);
  const posTex = gpu.createTexture();
  const velTex = gpu.createTexture();
  const pd = posTex.image.data as unknown as Float32Array;
  for (let i = 0; i < count; i++) {
    pd[i * 4 + 0] = data.initial[i * 3 + 0];
    pd[i * 4 + 1] = data.initial[i * 3 + 1];
    pd[i * 4 + 2] = data.initial[i * 3 + 2];
    pd[i * 4 + 3] = 1;
  }

  const velVar = gpu.addVariable("textureVelocity", velocityFrag, velTex);
  const posVar = gpu.addVariable("texturePosition", positionFrag, posTex);
  gpu.setVariableDependencies(velVar, [velVar, posVar]);
  gpu.setVariableDependencies(posVar, [velVar, posVar]);

  const vu = velVar.material.uniforms;
  vu.uTime = { value: 0 };
  vu.uForm = { value: 0 };
  vu.uDelta = { value: 0 };
  vu.uCursorOrigin = { value: new THREE.Vector3() };
  vu.uCursorDir = { value: new THREE.Vector3(0, 0, -1) };
  vu.uCursorActive = { value: 0 };
  vu.uOpenId = { value: -1 };
  vu.uOpen = { value: 0 };
  vu.uOpenR = { value: 3 };
  vu.uCamRight = { value: new THREE.Vector3(1, 0, 0) };
  vu.uCamUp = { value: new THREE.Vector3(0, 1, 0) };
  vu.uForward = { value: new THREE.Vector3(0, 0, -1) };
  vu.uLocal = { value: localTex };
  vu.uOrbit = { value: orbitTex };
  vu.uMisc = { value: miscTex };
  posVar.material.uniforms.uDelta = { value: 0 };

  const err = gpu.init();
  if (err) throw new Error(`GPUComputationRenderer: ${err}`);

  return { gpu, posVar, vu, localTex, orbitTex, miscTex };
}
