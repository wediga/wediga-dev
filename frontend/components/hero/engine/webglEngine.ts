// WebGL-GPGPU hero engine. A GPUComputationRenderer runs the atom simulation as
// ping-pong float textures, a single Points object reads the position texture,
// and scroll drives an on-rails camera through the section planets, opening each
// into a disc that backs the DOM section text.
//
// The motion contract (start framing, camera legs, pitch clamp, scroll rates,
// scrim sizing, open spring) is frozen and mirrors the approved sandbox exactly.
//
// createWebglEngine is the wiring: it builds the renderer, scene, camera and
// poses, calls the sub-builders, then runs the per-frame loop.

import * as THREE from "three";
import { generateStarSystem } from "./starSystem";
import { buildGpgpu } from "./gpgpu";
import { buildPoints } from "./points";
import { buildOrbitLines } from "./orbitLines";
import { buildPointer } from "./pointer";
import { buildRailsCamera } from "./railsCamera";
import { clampPitch, stepOpenSpring } from "./frameMath";
import type { EngineCallbacks, EngineHandle, HeroConfig } from "./types";

export async function createWebglEngine(
  canvas: HTMLCanvasElement,
  config: HeroConfig,
  callbacks: EngineCallbacks,
): Promise<EngineHandle> {
  // Round the requested atom count up to a square texture.
  const texSize = Math.max(8, Math.ceil(Math.sqrt(config.atomCount)));
  const count = texSize * texSize;
  // Clamped to >= 2: a single stop has no journey and divides by zero in the
  // per-leg maths. The generator is told the count so it yields enough planets.
  const STATIONS = Math.max(2, Math.round(config.stationCount));
  const data = generateStarSystem(count, config.seed, STATIONS);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    alpha: false,
    powerPreference: "high-performance",
  });
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  renderer.setPixelRatio(pixelRatio);
  renderer.setClearColor(0x05060a, 1);

  const scene = new THREE.Scene();

  let maxOrbit = 1;
  for (let i = 0; i < count; i++) maxOrbit = Math.max(maxOrbit, data.orbit[i * 4]);
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 400);
  // Overview pose: frame the whole system before the first scroll. Distance from
  // the outer orbit and the field of view so nothing clips; recomputed on resize.
  const overviewPos = new THREE.Vector3();
  function computeOverview() {
    const systemRadius = maxOrbit + 2.5;
    const aspect = camera.aspect || 1;
    const vTan = Math.tan(((camera.fov * Math.PI) / 180) / 2);
    const fit = (systemRadius / (vTan * Math.min(1, aspect))) * 0.88;
    overviewPos.set(0, fit * 0.34, fit * 0.94);
  }
  computeOverview();
  camera.position.copy(overviewPos);
  camera.lookAt(0, 0, 0);

  // Quiet pose: a fixed framing of the sun alone, no ride. The sun fills the
  // smaller viewport dimension but leaves margin so cursor-pushed points can move
  // out and ease back without clipping at the canvas edge. Reduced motion only; in
  // full motion it is computed but never read.
  const QUIET_SUN_FILL = 0.8;
  const quietPos = new THREE.Vector3();
  const quietDir = new THREE.Vector3(0, 0.17, 0.99).normalize();
  function computeQuiet() {
    const r = data.meta.sunRadius;
    const aspect = camera.aspect || 1;
    const vTan = Math.tan(((camera.fov * Math.PI) / 180) / 2);
    const dist = r / (QUIET_SUN_FILL * vTan * Math.min(1, aspect));
    quietPos.copy(quietDir).multiplyScalar(dist);
  }
  computeQuiet();

  // --- sub-builders -------------------------------------------------------
  // Each returns a handle over its own state; the shared pieces the loop needs
  // come back explicitly.
  const { gpu, posVar, vu, localTex, orbitTex, miscTex } = buildGpgpu(
    renderer,
    texSize,
    count,
    data,
  );
  const { pointsGeo, pointsMat } = buildPoints(
    scene,
    data,
    count,
    texSize,
    pixelRatio,
  );
  const { setOrbitOpacity, dispose: disposeOrbitLines } = buildOrbitLines(
    scene,
    data,
  );
  const { updateCursor, dispose: disposePointer } = buildPointer(
    canvas,
    camera,
    vu,
  );
  const {
    assignments,
    planetPosAt,
    updateWaypoints,
    scrollProgress,
    mapScroll,
    orbitLerp,
    camPts,
    stationCam,
    lookPts,
  } = buildRailsCamera(data, STATIONS, config.seed);

  // --- resize -------------------------------------------------------------
  function resize() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    computeOverview();
    computeQuiet();
  }
  resize();
  const ro = new ResizeObserver(resize);
  ro.observe(canvas);

  // --- shared per-frame state ---------------------------------------------
  const ORIGIN = new THREE.Vector3();
  const railsPos = new THREE.Vector3();
  const railsLook = new THREE.Vector3();
  const camLook = new THREE.Vector3();
  const fwd = new THREE.Vector3();
  const camRight = new THREE.Vector3();
  const camUp = new THREE.Vector3();
  const worldUp = new THREE.Vector3(0, 1, 0);
  const projV = new THREE.Vector3();
  const edgeV = new THREE.Vector3();
  let pSmooth = 0; // smoothed scroll progress, removes wheel-step jolts
  let dockedSmooth = 0;
  // Scrim/text opacity follows the same spring the atoms use (k=14, c=4.5), so the
  // darkening tracks the visible planet form rather than the open target.
  let openVisual = 0;
  let openVel = 0;
  // Last healthy horizontal look direction, reused when the camera is straight
  // above the look target so the pitch clamp still has a side to bow to.
  let lastHx = 0;
  let lastHz = 1;

  // --- loop ---------------------------------------------------------------
  let lastT = performance.now();
  let formTime = 0;
  let simTime = 0;
  let raf = 0;
  let running = true;

  // Orient the camera and publish the basis the camera-facing backing disc reads.
  // Identical in the full and quiet paths.
  function setCameraBasis(lookTarget: THREE.Vector3) {
    camera.up.set(0, 1, 0);
    camera.lookAt(lookTarget);
    camera.updateMatrixWorld();

    camera.getWorldDirection(fwd);
    camRight.crossVectors(fwd, worldUp).normalize();
    camUp.crossVectors(camRight, fwd).normalize();
    vu.uCamRight.value.copy(camRight);
    vu.uCamUp.value.copy(camUp);
    vu.uForward.value.copy(fwd);
  }

  // Drive the rails camera from the smoothed scroll: ease the dampers, blend the
  // overview fly-in (b), run the station bezier and the orbit-lerp, set
  // camera.position and camLook. Returns the scroll mapping and the blend b.
  function scrollToCameraPose(dt: number): {
    m: ReturnType<typeof mapScroll>;
    b: number;
  } {
    pSmooth += (scrollProgress() - pSmooth) * (1 - Math.exp(-0.7 * dt));
    const m = mapScroll(pSmooth);
    dockedSmooth += (m.docked - dockedSmooth) * (1 - Math.exp(-7 * dt));
    // Blend from the overview into the rails: forming first, then the lead-in
    // (m.approach) flies from the overview to the first station.
    const b = Math.min(1, Math.max(0, (formTime - 2.2) / 1.4)) * m.approach;
    updateWaypoints(simTime);
    // Travel as an orbit around the sun, the short way, so the path sweeps around
    // the side and never arcs over the top, even when the next station sits
    // opposite through the sun. Height lerps straight between station heights, the
    // look target between planet centres, keeping the view low through the turn.
    const segF = m.u * (STATIONS - 1);
    const seg = Math.min(STATIONS - 2, Math.max(0, Math.floor(segF)));
    const lt2 = segF - seg;
    // Station travel: a quadratic bezier through the outward midpoint, so the path
    // bows gently around the bodies.
    const omt = 1 - lt2;
    const ctrl = camPts[2 * seg + 1];
    railsPos
      .set(0, 0, 0)
      .addScaledVector(stationCam[seg], omt * omt)
      .addScaledVector(ctrl, 2 * omt * lt2)
      .addScaledVector(stationCam[seg + 1], lt2 * lt2);
    railsLook.lerpVectors(lookPts[seg], lookPts[seg + 1], lt2);
    // The overview fly-in is an orbit around the side, not a straight lerp, so the
    // camera comes in from the side when the first station sits far. Endpoints
    // unchanged; at b=1 this returns railsPos exactly.
    orbitLerp(overviewPos, railsPos, b, camera.position);
    camLook.lerpVectors(ORIGIN, railsLook, b);
    return { m, b };
  }

  // Project the open planet's disc to screen: its centre plus a point one disc
  // radius up in camera space give the screen centre and radius (atoms expand on
  // open, so the disc is bigger than the body). Sets the disc world-radius uniform
  // and returns the screen placement for the DOM text.
  function projectDiscToScreen(dist: number): {
    sx: number;
    sy: number;
    screenR: number;
  } {
    const cw = canvas.clientWidth || window.innerWidth;
    const chh = canvas.clientHeight || window.innerHeight;
    const fovRad = (camera.fov * Math.PI) / 180;
    const focalPx = chh / 2 / Math.tan(fovRad / 2);
    // The disc fills most of the viewport, scaling with the window. Height-bound on
    // landscape, width-bound on portrait so it never spills past the sides.
    const targetScreenR = Math.min(chh * 0.45, cw * 0.46);
    const discWorldR = (targetScreenR * dist) / focalPx;
    vu.uOpenR.value = discWorldR;
    const worldR = discWorldR;
    edgeV.copy(projV).addScaledVector(camUp, worldR);
    edgeV.project(camera);
    projV.project(camera);
    const sx = (projV.x * 0.5 + 0.5) * cw;
    const sy = (-projV.y * 0.5 + 0.5) * chh;
    const ex = (edgeV.x * 0.5 + 0.5) * cw;
    const ey = (-edgeV.y * 0.5 + 0.5) * chh;
    const screenR = Math.hypot(ex - sx, ey - sy);
    return { sx, sy, screenR };
  }

  function renderFrame(delta: number) {
    const dt = Math.min(delta, 1 / 30);
    // Calm the system while docked so orbiting and spinning stop moving the target,
    // and the atoms settle into the planet form instead of lagging off-centre.
    const timeScale = 1 - dockedSmooth * 0.9;
    simTime += dt * 0.5 * timeScale;
    formTime += dt * 0.6;
    vu.uTime.value = simTime;
    vu.uForm.value = formTime;
    vu.uDelta.value = dt;
    posVar.material.uniforms.uDelta.value = dt;
    updateCursor();

    const formProg = Math.min(1, Math.max(0, (formTime - 2.2) / 1.0));

    const { m, b } = scrollToCameraPose(dt);
    // Guard against a roll-over: keep the pitch below MAX_PITCH so lookAt with a
    // world-up never flips the horizon. Only nudges in a degenerate near-overhead
    // pose; at every station the pitch is ~20deg, so it never touches normal framing.
    const pitched = clampPitch(
      camera.position.x,
      camera.position.y,
      camera.position.z,
      camLook.x,
      camLook.y,
      camLook.z,
      lastHx,
      lastHz,
    );
    camera.position.x = pitched.x;
    camera.position.z = pitched.z;
    lastHx = pitched.lastHx;
    lastHz = pitched.lastHz;
    setCameraBasis(camLook);

    const planetIndex = assignments[m.station];
    planetPosAt(planetIndex, simTime, projV);
    const dist = camera.position.distanceTo(projV);
    const openAmt = dockedSmooth * b;
    // Spring identical to the atoms' (k=14, c=4.5), so the scrim/text opacity tracks
    // the visible planet form.
    const spring = stepOpenSpring(openVisual, openVel, openAmt, dt);
    openVisual = spring.openVisual;
    openVel = spring.openVel;
    const openVis = spring.openVis;
    const orbitDim = openAmt;
    vu.uOpenId.value = planetIndex;
    vu.uOpen.value = openAmt;
    pointsMat.uniforms.uOpenId.value = planetIndex;
    pointsMat.uniforms.uOpen.value = openAmt;
    pointsMat.uniforms.uDim.value = openAmt;

    const { sx, sy, screenR } = projectDiscToScreen(dist);
    callbacks.onStation(m.station, openVis, sx, sy, screenR);

    // Orbit lines appear after forming and step back while text is open.
    setOrbitOpacity(formProg * (1 - orbitDim * 0.85));

    gpu.compute();
    const tex = gpu.getCurrentRenderTarget(posVar).texture;
    pointsMat.uniforms.uPositions.value = tex;

    renderer.render(scene, camera);
  }

  function loop() {
    if (!running) return;
    raf = requestAnimationFrame(loop);
    const now = performance.now();
    const delta = (now - lastT) / 1000;
    lastT = now;
    renderFrame(delta);
  }

  // Quiet mode frame: a cursor-reactive sun from a fixed pose. No rails, no scroll
  // read, no station opening. The reduced-motion path's whole render.
  function renderQuietFrame(delta: number) {
    const dt = Math.min(delta, 1 / 30);
    // Advance the sim for the slow self-spin, and hold uForm past every atom's
    // delay so the sun stays fully formed.
    simTime += dt * 0.5;
    formTime += dt * 0.6;
    vu.uTime.value = simTime;
    vu.uForm.value = formTime;
    vu.uDelta.value = dt;
    posVar.material.uniforms.uDelta.value = dt;
    updateCursor();

    // Fixed pose framing the sun; no rails maths runs.
    camera.position.copy(quietPos);
    setCameraBasis(ORIGIN);

    // No planet ever opens in quiet mode.
    vu.uOpen.value = 0;
    vu.uOpenId.value = -1;
    pointsMat.uniforms.uOpen.value = 0;
    pointsMat.uniforms.uOpenId.value = -1;
    pointsMat.uniforms.uDim.value = 0;

    gpu.compute();
    pointsMat.uniforms.uPositions.value =
      gpu.getCurrentRenderTarget(posVar).texture;
    renderer.render(scene, camera);
  }

  function quietLoop() {
    if (!running) return;
    raf = requestAnimationFrame(quietLoop);
    const now = performance.now();
    const delta = (now - lastT) / 1000;
    lastT = now;
    renderQuietFrame(delta);
  }

  // One loop per mode, so the background-pause resume restarts the right one.
  const tick = config.reducedMotion ? quietLoop : loop;

  function onVisibility() {
    if (document.hidden) {
      running = false;
      cancelAnimationFrame(raf);
    } else if (!running) {
      running = true;
      lastT = performance.now();
      tick();
    }
  }
  document.addEventListener("visibilitychange", onVisibility);

  if (config.reducedMotion) {
    // Quiet mode: sun alone, pre-settle the atoms so it starts already formed with
    // no entrance impulse, then run the loop.
    pointsMat.uniforms.uSunOnly.value = 1;
    setOrbitOpacity(0);
    formTime = 6;
    vu.uForm.value = formTime;
    vu.uOpen.value = 0;
    vu.uOpenId.value = -1;
    for (let s = 0; s < 280; s++) {
      vu.uTime.value = simTime;
      vu.uDelta.value = 1 / 60;
      posVar.material.uniforms.uDelta.value = 1 / 60;
      gpu.compute();
    }
    lastT = performance.now();
    quietLoop();
  } else {
    loop();
  }

  return {
    atomCount: count,
    planetCount: data.meta.planetCount,
    // The generated colours, sun plus one base colour per planet, from the meta the
    // render uses. Exposed for the site's generative UI accent.
    systemColors: {
      sun: data.meta.sunColor,
      planets: data.meta.planets.map((p) => p.color),
    },
    dispose() {
      running = false;
      cancelAnimationFrame(raf);
      document.removeEventListener("visibilitychange", onVisibility);
      disposePointer();
      ro.disconnect();
      disposeOrbitLines();
      pointsGeo.dispose();
      pointsMat.dispose();
      localTex.dispose();
      orbitTex.dispose();
      miscTex.dispose();
      gpu.dispose();
      renderer.dispose();
    },
  };
}
