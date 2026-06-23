// WebGL-GPGPU hero engine. A WebGLRenderer plus a GPUComputationRenderer runs the
// atom simulation on the GPU as ping-pong float textures; a single Points object
// reads the position texture each frame. The scroll position drives an on-rails
// camera along a fixed path through the section planets, opening each one into a
// disc that backs the DOM section text.
//
// The motion contract (start framing, camera legs, pitch clamp, scroll rates,
// scrim sizing, open spring) is frozen and mirrors the approved sandbox exactly.
//
// createWebglEngine is the slim wiring: it builds the renderer, scene, camera and
// poses, calls the focused sub-builders (gpgpu, points, orbit lines, pointer,
// rails camera), then runs the per-frame loop that ties them together. Each
// sub-builder takes explicit inputs and returns an explicit handle, so the shared
// state stays visible here rather than hidden in one closure.

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
  // Section stops the rails ride through; one planet anchors each. Driven by the
  // section count so adding a section just adds a stop. Clamped to >= 2 (a single
  // stop has no journey and would divide by zero in the per-leg maths). The
  // generator is told the count so it always yields at least that many planets.
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
  // Overview pose: frame the WHOLE system in the viewport before the first scroll.
  // The distance comes from the outer orbit and the field of view so nothing is
  // clipped, recomputed on resize for the current aspect ratio.
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

  // Quiet pose: a fixed, static framing of the sun alone, no ride. The sun fills
  // a generous part of the smaller viewport dimension so it reads as a dominant
  // anchor, but it deliberately leaves margin inside the canvas so the
  // cursor-pushed points have room to move out and ease back without being
  // clipped at the canvas edge. Recomputed on resize for the current aspect.
  // Only used in reduced motion; in full motion it is computed but never read.
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
  // Each returns a small handle over its own state; the shared pieces the loop
  // needs (the velocity uniforms, the position variable, the points material, the
  // orbit-line fade, the cursor update, the rails maths) come back explicitly.
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
  // Scrim/text opacity follows the SAME spring the atoms use (k=14, c=4.5), so the
  // darkening spreads exactly as fast as the planet visibly forms, and recedes at the
  // same rate on the way out, instead of running ahead of the open target.
  let openVisual = 0;
  let openVel = 0;
  // Last healthy horizontal look direction, reused when the camera is momentarily
  // straight above the look target so the pitch clamp still has a side to bow to.
  let lastHx = 0;
  let lastHz = 1;

  // --- loop ---------------------------------------------------------------
  // Manual frame delta in seconds (replaces the deprecated THREE.Clock, same maths).
  let lastT = performance.now();
  let formTime = 0;
  let simTime = 0;
  let raf = 0;
  let running = true;

  // Orient the camera at a look target and publish the camera basis the
  // camera-facing backing disc reads. Identical in the full and quiet paths.
  function setCameraBasis(lookTarget: THREE.Vector3) {
    camera.up.set(0, 1, 0);
    camera.lookAt(lookTarget);
    camera.updateMatrixWorld();

    // Camera basis for the camera-facing backing disc.
    camera.getWorldDirection(fwd);
    camRight.crossVectors(fwd, worldUp).normalize();
    camUp.crossVectors(camRight, fwd).normalize();
    vu.uCamRight.value.copy(camRight);
    vu.uCamUp.value.copy(camUp);
    vu.uForward.value.copy(fwd);
  }

  // Drive the rails camera from the smoothed scroll: ease the pSmooth/dockedSmooth
  // dampers, blend the overview-to-first-station fly-in (b), run the
  // station-to-station quadratic bezier and the azimuthal orbit-lerp, and set
  // camera.position and camLook. Returns the scroll mapping and the overview->rails
  // blend the rest of the frame still needs. Pure relocation of the inline block:
  // it mutates the same shared dampers and scratch vectors in the same order.
  function scrollToCameraPose(dt: number): {
    m: ReturnType<typeof mapScroll>;
    b: number;
  } {
    pSmooth += (scrollProgress() - pSmooth) * (1 - Math.exp(-0.7 * dt));
    const m = mapScroll(pSmooth);
    dockedSmooth += (m.docked - dockedSmooth) * (1 - Math.exp(-7 * dt));
    // Blend from the overview into the rails: forming first, then the scroll
    // lead-in (m.approach) flies from the overview to the first station.
    const b = Math.min(1, Math.max(0, (formTime - 2.2) / 1.4)) * m.approach;
    updateWaypoints(simTime);
    // Travel as an azimuthal orbit around the sun: interpolate the camera's angle
    // around the centre the short way (left or right), plus its radius and height,
    // so the path always sweeps around the SIDE of the system and never arcs over
    // the top, even when the next station sits directly opposite through the sun.
    // The height is a straight lerp between the two station heights, so the camera
    // can never rise above the anlage. The look target lerps between the two planet
    // centres, which keeps the view low and horizontal through the turn.
    const segF = m.u * (STATIONS - 1);
    const seg = Math.min(STATIONS - 2, Math.max(0, Math.floor(segF)));
    const lt2 = segF - seg;
    // Station-to-station travel: a quadratic bezier through the outward midpoint,
    // so the path bows gently around the bodies with an even, smooth felt speed.
    const omt = 1 - lt2;
    const ctrl = camPts[2 * seg + 1];
    railsPos
      .set(0, 0, 0)
      .addScaledVector(stationCam[seg], omt * omt)
      .addScaledVector(ctrl, 2 * omt * lt2)
      .addScaledVector(stationCam[seg + 1], lt2 * lt2);
    railsLook.lerpVectors(lookPts[seg], lookPts[seg + 1], lt2);
    // The fly-in from the overview is an orbit around the side (not a straight
    // lerp), so the camera comes in from the side instead of crossing straight over
    // the system when the first station sits on the far side. Endpoints unchanged,
    // only the path between them; at b=1 (every leg) this returns railsPos exactly.
    orbitLerp(overviewPos, railsPos, b, camera.position);
    camLook.lerpVectors(ORIGIN, railsLook, b);
    return { m, b };
  }

  // Project the open planet's disc to screen: its centre, plus a point one disc
  // radius "up" in camera space, gives the screen centre and the screen radius of
  // the visible disc (the atoms expand on open, so the disc is bigger than the
  // body). Sets the disc world-radius uniform and returns the screen placement for
  // the DOM text. Pure relocation of the inline block; mutates the same projV/edgeV
  // scratch vectors in the same order.
  function projectDiscToScreen(dist: number): {
    sx: number;
    sy: number;
    screenR: number;
  } {
    const cw = canvas.clientWidth || window.innerWidth;
    const chh = canvas.clientHeight || window.innerHeight;
    // The open disc radius is uOpenR (a camera-facing disc in the shader). Size it
    // so its screen radius always exceeds the text box, derived from the text width
    // and converted to a world radius at this distance.
    const fovRad = (camera.fov * Math.PI) / 180;
    const focalPx = chh / 2 / Math.tan(fovRad / 2);
    // The open disc fills most of the viewport so the planet, and the text on it,
    // reads large on any screen, scaling with the window instead of a fixed pixel
    // size. Height-bound on landscape (fills to just shy of the top and bottom edge),
    // width-bound on portrait so it never spills past the sides.
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
    // Calm the whole system while docked at a card so the orbiting and spinning
    // stop moving the target; the atoms then settle exactly into the planet form
    // instead of lagging behind a moving target, which kept the cloud off-centre.
    const timeScale = 1 - dockedSmooth * 0.9;
    simTime += dt * 0.5 * timeScale;
    formTime += dt * 0.6;
    vu.uTime.value = simTime;
    vu.uForm.value = formTime;
    vu.uDelta.value = dt;
    posVar.material.uniforms.uDelta.value = dt;
    updateCursor();

    const formProg = Math.min(1, Math.max(0, (formTime - 2.2) / 1.0));

    // Drive the rails camera from the smoothed scroll: dampers, overview fly-in
    // blend, station-to-station bezier and the azimuthal orbit-lerp. Sets
    // camera.position and camLook; returns the scroll mapping and the blend b.
    const { m, b } = scrollToCameraPose(dt);
    // Hard guarantee against a roll-over: keep the view pitch below MAX_PITCH so the
    // forward vector never approaches vertical, the angle at which lookAt with a
    // world-up flips the horizon. Only nudges in a degenerate near-overhead pose; at
    // every station the pitch is ~20deg, so this never touches the normal framing.
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
    // Run a spring identical to the atoms' (k=14, c=4.5) toward the open target, so
    // the scrim/text opacity tracks the visible planet form instead of the target.
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

    // Project the open planet's disc to screen (centre and radius) and size the
    // disc world-radius uniform, then hand the DOM text its screen placement.
    const { sx, sy, screenR } = projectDiscToScreen(dist);
    callbacks.onStation(m.station, openVis, sx, sy, screenR);

    // Orbit lines appear after forming and step back while a text is open.
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

  // Quiet mode frame: a living, cursor-reactive sun from a fixed pose. No rails,
  // no scroll read, no station opening, only the sun. This is the reduced-motion
  // path's whole render; the full-motion renderFrame above is left untouched.
  function renderQuietFrame(delta: number) {
    const dt = Math.min(delta, 1 / 30);
    // Gentle life: advance the sim so the sun keeps its slow self-spin, and hold
    // uForm well past every atom's delay so the sun stays fully formed.
    simTime += dt * 0.5;
    formTime += dt * 0.6;
    vu.uTime.value = simTime;
    vu.uForm.value = formTime;
    vu.uDelta.value = dt;
    posVar.material.uniforms.uDelta.value = dt;
    updateCursor();

    // Fixed pose framing the sun at the origin. No rails maths runs at all.
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
    // Quiet mode: render the sun alone (planets and orbit lines hidden) and
    // pre-settle the atoms so the sun starts already formed, with no entrance
    // impulse. Then run the living loop: slow spin plus cursor reaction, no ride.
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
    // Read-only: the system's generated colours, the sun plus one base colour
    // per planet, taken straight from the generator's meta the render already
    // uses. Exposed for the site's generative UI accent, no render change.
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
