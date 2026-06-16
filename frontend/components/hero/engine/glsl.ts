// GLSL for the WebGL-GPGPU hero. The simulation lives in two compute passes
// (velocity then position) run by GPUComputationRenderer, and the look lives in a
// single render material (lit points). The motion model is "spring to a slowly
// moving target": each atom is pulled toward its home on a body whose centre
// orbits the sun and whose surface offset slowly spins, so the finished system
// keeps circling without any gravity integration.

// Compute: velocity. Reads the atom's home (orbit + local offset textures), ramps
// a spring in as the impulse wave reaches it, adds an idle swirl before forming
// and a dezent cursor push.
export const velocityFrag = /* glsl */ `
uniform float uTime;
uniform float uForm;
uniform float uDelta;
uniform vec3 uCursorOrigin;
uniform vec3 uCursorDir;
uniform float uCursorActive;
uniform float uOpenId;   // planet index currently opening, -1 if none
uniform float uOpen;     // open amount 0..1
uniform float uOpenR;    // world radius of the camera-facing backing disc
uniform vec3 uCamRight;  // camera basis, for the camera-facing disc
uniform vec3 uCamUp;
uniform vec3 uForward;
uniform sampler2D uLocal;
uniform sampler2D uOrbit;
uniform sampler2D uMisc;

vec3 rotateY(vec3 p, float a) {
  float c = cos(a), s = sin(a);
  return vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z);
}

// Two decorrelated pseudo-randoms per atom from its integer cell in the compute
// texture. A sin-free fract hash (Dave Hoskins style) fed the integer cell, which
// stays robust where a sin hash loses precision at large indices (the cause of the
// spoke and spiral artefacts).
vec2 cellHash() {
  vec2 g = floor(gl_FragCoord.xy); // integer cell, one per atom
  vec3 p3 = fract(vec3(g.x, g.y, g.x) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.xx + p3.yz) * p3.zy);
}

void main() {
  vec2 uv = gl_FragCoord.xy / resolution.xy;
  vec3 pos = texture2D(texturePosition, uv).xyz;
  vec3 vel = texture2D(textureVelocity, uv).xyz;
  vec4 localData = texture2D(uLocal, uv);
  vec3 local = localData.xyz;
  float bodyId = localData.w;            // -1 sun, else planet index
  vec4 orb = texture2D(uOrbit, uv);   // radius, phase, speed, inclination
  vec4 m = texture2D(uMisc, uv);      // delay, spinSpeed, kind, shade

  float ang = orb.y + uTime * orb.z;
  vec3 base = vec3(cos(ang) * orb.x, 0.0, sin(ang) * orb.x);
  float ci = cos(orb.w), si = sin(orb.w);
  vec3 center = vec3(base.x, -base.z * si, base.z * ci);

  vec3 rotLocal = rotateY(local, uTime * m.y);

  // Open: the docked planet's atoms gather into a filled, camera-facing disc that
  // backs the DOM text and hides the background behind it. A uniform disc (r via
  // sqrt) so it reads as a solid container, not a ring with a hole.
  float open = 0.0;
  if (uOpen > 0.001 && bodyId > -0.5 && abs(bodyId - uOpenId) < 0.5) {
    open = uOpen;
  }
  vec2 h = cellHash();
  float rr = uOpenR * sqrt(h.x);
  float th = 6.28318530718 * h.y;
  vec3 disc = center
    + uCamRight * (rr * cos(th))
    + uCamUp * (rr * sin(th))
    + uForward * (uOpenR * 0.12);
  vec3 shellTarget = center + rotLocal;
  vec3 target = mix(shellTarget, disc, open);

  // The impulse is a wave: an atom only starts springing once uForm passes its
  // per-atom delay, so the sun resolves first and the rim last.
  float act = smoothstep(m.x, m.x + 0.9, uForm);

  vec3 accel = (target - pos) * (14.0 * act);

  // Before its turn the atom drifts in a slow swirl so the raw cloud stays alive.
  float idle = 1.0 - act;
  accel += vec3(-pos.z, pos.x * 0.15, pos.x) * 0.04 * idle;

  // Cursor as a ray from the camera through the pointer. Atoms are pushed by their
  // perpendicular distance to that ray, so the influence reaches every depth and
  // every orbit height, including the tilted outer planets that the old flat
  // y = 0 projection missed.
  if (uCursorActive > 0.5) {
    vec3 toPos = pos - uCursorOrigin;
    float along = max(dot(toPos, uCursorDir), 0.0);
    vec3 closest = uCursorOrigin + uCursorDir * along;
    vec3 d = pos - closest;
    float dist = length(d);
    float R = 5.0;
    if (dist < R && dist > 0.0001) {
      float f = 1.0 - dist / R;
      accel += normalize(d) * f * f * 7.0;
    }
  }

  vel += accel * uDelta;
  vel *= exp(-4.5 * uDelta); // frame-rate independent damping

  gl_FragColor = vec4(vel, 1.0);
}
`;

// Compute: position. Plain integration of the velocity just written this frame.
export const positionFrag = /* glsl */ `
uniform float uDelta;

void main() {
  vec2 uv = gl_FragCoord.xy / resolution.xy;
  vec3 pos = texture2D(texturePosition, uv).xyz;
  vec3 vel = texture2D(textureVelocity, uv).xyz;
  pos += vel * uDelta;
  gl_FragColor = vec4(pos, 1.0);
}
`;

// Render: lit points. Position is read from the computed texture; brightness is
// monochrome with per-atom variance. The cloud look (size, softness, intensity)
// is fixed by uniforms set once at build time.
export const pointsVert = /* glsl */ `
uniform sampler2D uPositions;
uniform float uSizeScale;
uniform float uPixelRatio;
uniform float uOpenId;
uniform float uOpen;
uniform float uDim;       // how much the rest of the system steps back (0..1)
attribute vec2 reference;
attribute float aSize;
attribute float aShade;
attribute float aBodyId;
attribute vec3 aColor;
varying float vShade;
varying vec3 vColor;
varying float vDim;
varying float vOpen;

void main() {
  vec3 pos = texture2D(uPositions, reference).xyz;
  vShade = aShade;
  vColor = aColor;
  float isOpen = (aBodyId > -0.5 && abs(aBodyId - uOpenId) < 0.5) ? 1.0 : 0.0;
  vOpen = isOpen * uOpen;
  // Everything except the docked planet steps back while a text is open.
  vDim = mix(mix(1.0, 0.16, uDim), 1.0, isOpen);
  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mv;
  // Atoms stay fine grains even up close and even while a planet opens. The open
  // planet covers the background through density and opacity (see the fragment),
  // not by fattening into blobs.
  float size = aSize * uSizeScale * uPixelRatio * (14.0 / max(-mv.z, 3.5));
  gl_PointSize = clamp(size, 1.0, 18.0);
}
`;

export const pointsFrag = /* glsl */ `
uniform float uSoftness;
uniform float uIntensity;
varying float vShade;
varying vec3 vColor;
varying float vDim;
varying float vOpen;

void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c) * 2.0;
  float edge = mix(0.45, 0.98, uSoftness);
  float alpha = smoothstep(1.0, 1.0 - edge, d);
  if (alpha <= 0.001) discard;
  // Per-atom colour, lifted by the shade and a soft centre so each grain reads
  // like a lit point rather than a flat dot. Hue comes from the generator.
  float lum = mix(0.72, 1.05, vShade);
  float centre = 1.0 + (1.0 - d) * 0.35;
  // The opened planet's grains turn near-opaque so the disc backs the text and
  // hides the field behind it; the rest dims back.
  float a = mix(alpha, min(1.0, alpha * 2.4 + 0.35), vOpen) * uIntensity;
  gl_FragColor = vec4(vColor * lum * centre * vDim, a);
}
`;
