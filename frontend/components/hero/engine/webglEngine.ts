// WebGL-GPGPU hero engine. A WebGLRenderer plus a GPUComputationRenderer runs the
// atom simulation on the GPU as ping-pong float textures; a single Points object
// reads the position texture each frame. The scroll position drives an on-rails
// camera along a fixed path through the section planets, opening each one into a
// disc that backs the DOM section text.
//
// The motion contract (start framing, camera legs, pitch clamp, scroll rates,
// scrim sizing, open spring) is frozen and mirrors the approved sandbox exactly.

import * as THREE from "three";
import { GPUComputationRenderer } from "three/examples/jsm/misc/GPUComputationRenderer.js";
import {
  velocityFrag,
  positionFrag,
  pointsVert,
  pointsFrag,
} from "./glsl";
import { generateStarSystem } from "./starSystem";
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

  // --- points object ------------------------------------------------------
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

  // Cloud look (individual lit points), fixed at build time: the form and body
  // toggles from the sandbox are gone, this is the single approved configuration.
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

  // --- orbital lines ------------------------------------------------------
  // One fine ring per planet, traced on the exact tilted path the planet follows.
  // They start invisible and only fade in once the forming is complete, so the
  // lines read as "the order is now set".
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
  // Drives the orbit-line fade from a forming-progress value (0..1).
  function setOrbitOpacity(progress: number) {
    for (const o of orbitLines) o.mat.opacity = progress * o.target;
  }

  // --- cursor (a ray from the camera through the pointer) -----------------
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
    // Pass the camera ray (origin + direction) instead of a flat-plane hit point,
    // so the push works at any depth and height, not just on y = 0.
    rayOrigin.copy(camera.position);
    rayDir.set(ndc.x, ndc.y, 0.5).unproject(camera).sub(rayOrigin).normalize();
    vu.uCursorOrigin.value.copy(rayOrigin);
    vu.uCursorDir.value.copy(rayDir);
    vu.uCursorActive.value = 1;
  }

  // --- resize -------------------------------------------------------------
  function resize() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    computeOverview();
  }
  resize();
  const ro = new ResizeObserver(resize);
  ro.observe(canvas);

  // --- rails camera -------------------------------------------------------
  // The scroll position drives the camera along a fixed path through the section
  // planets. Progress is read in the animation frame, never via a scroll listener,
  // so native scrolling stays untouched.

  // Random per load: which planet carries each section, in fixed section order.
  // Uses its own deterministic stream so it does not disturb the generator.
  function pickAssignments(s: number, planetCount: number): number[] {
    let a = (s ^ 0x9e3779b9) >>> 0;
    const rnd = () => {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const idx = Array.from({ length: planetCount }, (_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    // Always start at the outermost planet so the ride flies from OUTSIDE into the
    // system; the remaining stations are picked generatively from the rest. The
    // descending orbit-radius sort then orders the whole set outermost-first. (With
    // few stations a purely random pick could land the first stop mid-system, which
    // broke the "from outside in" feel.)
    let outer = 0;
    for (let i = 1; i < planetCount; i++) {
      if (
        data.meta.planets[i].orbitRadius > data.meta.planets[outer].orbitRadius
      ) {
        outer = i;
      }
    }
    const chosen = [
      outer,
      ...idx.filter((i) => i !== outer).slice(0, STATIONS - 1),
    ];
    chosen.sort(
      (a, b) =>
        data.meta.planets[b].orbitRadius - data.meta.planets[a].orbitRadius,
    );
    return chosen;
  }
  const assignments = pickAssignments(config.seed, data.meta.planets.length);

  // The scroll track is STATIONS+1 equal full-viewport snap sections (an overview
  // first, then one per station), so each leg is one snap step regardless of how far
  // apart the planets sit; the per-leg camera easing evens out the felt speed.

  const ORIGIN = new THREE.Vector3();
  const radial = new THREE.Vector3();
  function planetPosAt(planetIndex: number, t: number, out: THREE.Vector3) {
    const pl = data.meta.planets[planetIndex];
    const ang = pl.orbitPhase + t * pl.orbitSpeed;
    const bx = Math.cos(ang) * pl.orbitRadius;
    const bz = Math.sin(ang) * pl.orbitRadius;
    const si = Math.sin(pl.inclination);
    const ci = Math.cos(pl.inclination);
    return out.set(bx, -bz * si, bz * ci);
  }

  // Camera waypoints sit OUTSIDE each planet, so every station is approached from
  // outside. Between stations the path is a quadratic bezier through an outward
  // midpoint, so the curve bows gently around the bodies with an even felt speed.
  // The midpoint's outward direction is the bisector of the two stations' radial
  // directions; when the stations sit nearly opposite (the bisector collapses) it
  // bows perpendicular to the chord, so the curve always stays outside the system.
  // Seven control points: station k at index 2k, the midpoints at the odd indices.
  const camPts = Array.from(
    { length: 2 * STATIONS - 1 },
    () => new THREE.Vector3(),
  );
  const lookPts = Array.from({ length: STATIONS }, () => new THREE.Vector3());
  const stationCam = Array.from({ length: STATIONS }, () => new THREE.Vector3());
  function updateWaypoints(t: number) {
    let rim = 0;
    for (let k = 0; k < STATIONS; k++) {
      const pi = assignments[k];
      const pl = data.meta.planets[pi];
      planetPosAt(pi, t, lookPts[k]);
      radial.copy(lookPts[k]);
      if (radial.lengthSq() < 1e-4) radial.set(0, 0, 1);
      radial.normalize();
      stationCam[k]
        .copy(lookPts[k])
        .addScaledVector(radial, pl.radius * 3.4 + 6.0);
      stationCam[k].y += pl.radius * 1.2 + 2.6;
      camPts[2 * k].copy(stationCam[k]);
      rim = Math.max(rim, Math.hypot(stationCam[k].x, stationCam[k].z));
    }
    const clear = rim * 1.12 + 3;
    for (let k = 0; k < STATIONS - 1; k++) {
      const mid = camPts[2 * k + 1];
      const ax = stationCam[k].x, az = stationCam[k].z;
      const bx = stationCam[k + 1].x, bz = stationCam[k + 1].z;
      const la = Math.hypot(ax, az) || 1;
      const lb = Math.hypot(bx, bz) || 1;
      let dx = ax / la + bx / lb;
      let dz = az / la + bz / lb;
      let dl = Math.hypot(dx, dz);
      if (dl < 0.25) {
        const cx = bx - ax, cz = bz - az;
        dx = -cz;
        dz = cx;
        dl = Math.hypot(dx, dz) || 1;
      }
      mid.x = (dx / dl) * clear;
      mid.z = (dz / dl) * clear;
      mid.y = (stationCam[k].y + stationCam[k + 1].y) * 0.5 + 3;
    }
  }

  function scrollProgress(): number {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (max <= 0) return 0;
    return Math.min(1, Math.max(0, window.scrollY / max));
  }

  // Maps scroll 0..1 to a curve param with a dwell band at each station and a
  // smoothstep travel band between, so the camera eases to a gentle stop at every
  // station instead of drifting between two.
  function mapScroll(p: number) {
    // p maps to x in [0, STATIONS] across the equal snap sections. x = 0 is the
    // overview, x = i (i >= 1) is station i-1, where the scroll snaps and the card
    // locks. Between snaps the camera eases from one station to the next.
    const x = p * STATIONS;
    // docked: 1 only right at a station, fading sharply to 0 a short way out and flat
    // 0 across the middle of a leg, so the text and its scrim are present ONLY while
    // actually parked, not lingering faintly across the whole travel. Driven by the
    // distance in x to the nearest station (x = 1..STATIONS), so it works for the
    // lead-in and every leg alike.
    const nearest = Math.max(1, Math.round(x));
    const dxs = Math.abs(x - nearest);
    const tt = Math.min(1, Math.max(0, (dxs - 0.05) / (0.24 - 0.05)));
    const docked = 1 - tt * tt * (3 - 2 * tt);
    if (x <= 1) {
      // Lead-in: overview to the first station. approach drives the camera fly-in.
      const e = x * x * (3 - 2 * x);
      return { u: 0, station: 0, docked, approach: e };
    }
    const s = Math.min(STATIONS - 1, Math.floor(x) - 1); // lower station of this leg
    if (s >= STATIONS - 1) {
      return { u: 1, station: STATIONS - 1, docked, approach: 1 };
    }
    const lt = Math.min(1, x - (s + 1)); // 0 at station s, 1 at station s+1
    const e = lt * lt * (3 - 2 * lt);
    return {
      u: (s + e) / (STATIONS - 1),
      station: e < 0.5 ? s : s + 1,
      docked,
      approach: 1,
    };
  }

  // Interpolate between two world points as an orbit around the sun: the azimuth
  // takes the shorter way (left or right), the radius and height lerp straight. The
  // camera therefore always travels around the SIDE of the system, never across or
  // over the top, no matter where start and end sit. Used both for station-to-station
  // travel and for the overview-to-first-station fly-in.
  function orbitLerp(
    from: THREE.Vector3,
    to: THREE.Vector3,
    s: number,
    out: THREE.Vector3,
  ) {
    const aAng = Math.atan2(from.z, from.x);
    let dAng = Math.atan2(to.z, to.x) - aAng;
    while (dAng > Math.PI) dAng -= 2 * Math.PI;
    while (dAng < -Math.PI) dAng += 2 * Math.PI;
    const ang = aAng + dAng * s;
    const aR = Math.hypot(from.x, from.z);
    const r = aR + (Math.hypot(to.x, to.z) - aR) * s;
    out.set(Math.cos(ang) * r, from.y + (to.y - from.y) * s, Math.sin(ang) * r);
  }

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

    // Smooth the raw scroll so wheel steps never jolt the camera. Heavily damped:
    // the snap moves the scroll position to the next stop almost instantly, but the
    // camera glides there slowly instead of teleporting.
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
    // Hard guarantee against a roll-over: keep the view pitch below MAX_PITCH so the
    // forward vector never approaches vertical, the angle at which lookAt with a
    // world-up flips the horizon. Only nudges in a degenerate near-overhead pose; at
    // every station the pitch is ~20deg, so this never touches the normal framing.
    const MAX_PITCH = (72 * Math.PI) / 180;
    const minTan = Math.tan(MAX_PITCH);
    let hdx = camera.position.x - camLook.x;
    let hdz = camera.position.z - camLook.z;
    const vdy = camera.position.y - camLook.y;
    let hLen = Math.hypot(hdx, hdz);
    if (hLen > 1e-3) {
      lastHx = hdx / hLen;
      lastHz = hdz / hLen;
    }
    const minH = Math.abs(vdy) / minTan;
    if (hLen < minH) {
      if (hLen < 1e-3) {
        hdx = lastHx;
        hdz = lastHz;
        hLen = 1;
      }
      const sc = minH / hLen;
      camera.position.x = camLook.x + hdx * sc;
      camera.position.z = camLook.z + hdz * sc;
    }
    camera.up.set(0, 1, 0);
    camera.lookAt(camLook);
    camera.updateMatrixWorld();

    // Camera basis for the camera-facing backing disc.
    camera.getWorldDirection(fwd);
    camRight.crossVectors(fwd, worldUp).normalize();
    camUp.crossVectors(camRight, fwd).normalize();
    vu.uCamRight.value.copy(camRight);
    vu.uCamUp.value.copy(camUp);
    vu.uForward.value.copy(fwd);

    const planetIndex = assignments[m.station];
    planetPosAt(planetIndex, simTime, projV);
    const dist = camera.position.distanceTo(projV);
    const openAmt = dockedSmooth * b;
    // Run a spring identical to the atoms' (k=14, c=4.5) toward the open target, so
    // the scrim/text opacity tracks the visible planet form instead of the target.
    openVel += (openAmt - openVisual) * 14 * dt;
    openVel *= Math.exp(-4.5 * dt);
    openVisual += openVel * dt;
    const openVis = Math.min(1, Math.max(0, openVisual));
    const orbitDim = openAmt;
    vu.uOpenId.value = planetIndex;
    vu.uOpen.value = openAmt;
    pointsMat.uniforms.uOpenId.value = planetIndex;
    pointsMat.uniforms.uOpen.value = openAmt;
    pointsMat.uniforms.uDim.value = openAmt;

    // Project the planet centre to screen, plus a point one disc-radius "up" in
    // camera space, so we get both the screen centre and the screen radius of the
    // visible disc (the atoms expand on open, so the disc is bigger than the body).
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

  function onVisibility() {
    if (document.hidden) {
      running = false;
      cancelAnimationFrame(raf);
    } else if (!running && !config.reducedMotion) {
      running = true;
      lastT = performance.now();
      loop();
    }
  }
  document.addEventListener("visibilitychange", onVisibility);

  if (config.reducedMotion) {
    // Settle to the formed system, then hold a single still frame from the overview
    // pose. No camera ride, no animation, no station opening.
    formTime = 6;
    vu.uForm.value = formTime;
    for (let s = 0; s < 280; s++) {
      vu.uTime.value = simTime;
      vu.uDelta.value = 1 / 60;
      posVar.material.uniforms.uDelta.value = 1 / 60;
      gpu.compute();
    }
    const tex = gpu.getCurrentRenderTarget(posVar).texture;
    pointsMat.uniforms.uPositions.value = tex;
    // The system is fully formed in the still frame, so the orbit lines are shown.
    setOrbitOpacity(1);
    renderer.render(scene, camera);
    running = false;
  } else {
    loop();
  }

  return {
    atomCount: count,
    planetCount: data.meta.planetCount,
    dispose() {
      running = false;
      cancelAnimationFrame(raf);
      document.removeEventListener("visibilitychange", onVisibility);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      ro.disconnect();
      orbitGroup.children.forEach((c) => {
        const line = c as THREE.Line;
        line.geometry.dispose();
        (line.material as THREE.Material).dispose();
      });
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
