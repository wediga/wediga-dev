"use client";

import { useEffect, useRef } from "react";

/**
 * Calm, near-monochrome cosmos behind the whole site.
 *
 * A single fixed canvas draws a prerendered starfield plus a small node network
 * that reacts to the cursor. Ported from the proven prototype: refs + rAF only
 * (no React state for mouse or scroll), an offscreen starfield copied per frame
 * via drawImage, a hard node cap, no ctx.filter, pause when the tab is hidden,
 * a reduced-motion still frame and full listener/loop cleanup on unmount.
 */

type Node = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  z: number;
  cap: boolean;
};

export default function CosmosBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const starCanvas = document.createElement("canvas");
    const starCtx = starCanvas.getContext("2d");
    if (!starCtx) return;

    let width = 0;
    let height = 0;
    let nodes: Node[] = [];
    let mx = -9999;
    let my = -9999;
    let looping = false;
    let visible = true;
    let rafId = 0;

    function buildStars() {
      if (!starCtx) return;
      starCanvas.width = width;
      starCanvas.height = height;
      starCtx.clearRect(0, 0, width, height);
      const count = Math.floor((width * height) / 5000);
      starCtx.fillStyle = "#cdd0e2";
      for (let i = 0; i < count; i++) {
        starCtx.globalAlpha = 0.12 + Math.random() * 0.5;
        const r = Math.random() < 0.08 ? 1.4 : 0.7;
        starCtx.beginPath();
        starCtx.arc(Math.random() * width, Math.random() * height, r, 0, 7);
        starCtx.fill();
      }
      starCtx.globalAlpha = 1;
    }

    function resize() {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      buildStars();
      const target = Math.max(
        120,
        Math.min(190, Math.floor((width * height) / 6500)),
      );
      if (nodes.length === 0) {
        for (let i = 0; i < target; i++) {
          const z = 0.16 + Math.random() * 0.84;
          nodes.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.28,
            vy: (Math.random() - 0.5) * 0.28,
            z,
            cap: false,
          });
        }
      }
    }

    function frame() {
      if (!ctx) return;
      looping = false;
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(starCanvas, 0, 0);

      for (let k = 0; k < nodes.length; k++) {
        const p = nodes[k];
        let cap = false;
        if (mx > -9000) {
          const dx = mx - p.x;
          const dy = my - p.y;
          const d = Math.hypot(dx, dy);
          if (d < 250) {
            const g = (1 - d / 250) * p.z;
            if (p.z > 0.62 && d < 160) cap = true;
            const inv = d || 1;
            // attraction toward the cursor plus a perpendicular swirl
            p.vx += (dx / inv) * g * 0.16;
            p.vy += (dy / inv) * g * 0.16;
            p.vx += (-dy / inv) * g * 0.5;
            p.vy += (dx / inv) * g * 0.5;
          }
        }
        p.vx *= 0.95;
        p.vy *= 0.95;
        p.vx += (Math.random() - 0.5) * 0.04;
        p.vy += (Math.random() - 0.5) * 0.04;
        const maxSpeed = 0.6 + p.z * 2.2;
        p.vx = Math.max(-maxSpeed, Math.min(maxSpeed, p.vx));
        p.vy = Math.max(-maxSpeed, Math.min(maxSpeed, p.vy));
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.vx = Math.abs(p.vx);
        if (p.x > width) p.vx = -Math.abs(p.vx);
        if (p.y < 0) p.vy = Math.abs(p.vy);
        if (p.y > height) p.vy = -Math.abs(p.vy);
        p.cap = cap;
      }

      // far nodes first, dim
      for (let k = 0; k < nodes.length; k++) {
        const p = nodes[k];
        if (p.z >= 0.38) continue;
        ctx.globalAlpha = 0.18 + p.z * 0.32;
        ctx.fillStyle = "#8389a8";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1 + p.z * 1.7, 0, 7);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // edges between the closer nodes
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].z < 0.42) continue;
        for (let j = i + 1; j < nodes.length; j++) {
          if (nodes[j].z < 0.42) continue;
          const a = nodes[i];
          const b = nodes[j];
          const ddx = a.x - b.x;
          const ddy = a.y - b.y;
          const dd = ddx * ddx + ddy * ddy;
          if (dd < 13456) {
            const f = 1 - Math.sqrt(dd) / 116;
            const acc = a.cap || b.cap;
            ctx.strokeStyle = acc
              ? `rgba(169,135,255,${f * 0.5})`
              : `rgba(198,200,218,${f * 0.12})`;
            ctx.lineWidth = acc ? 1 : 0.6;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // near nodes last, bright
      for (let k = 0; k < nodes.length; k++) {
        const p = nodes[k];
        if (p.z < 0.38) continue;
        ctx.globalAlpha = 0.4 + p.z * 0.58;
        ctx.fillStyle = p.cap
          ? "#cbb1ff"
          : p.z > 0.74
            ? "#eff1f9"
            : "#c2c4d6";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1 + p.z * 3, 0, 7);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      if (!reduce && visible) kick();
    }

    function kick() {
      if (looping) return;
      looping = true;
      rafId = requestAnimationFrame(frame);
    }

    function onResize() {
      resize();
      // Under reduced motion there is no rAF loop, so the still frame would be
      // lost after a resize (resize resets the canvas size, clearing it). Redraw
      // the starfield once so the cosmos does not go blank until reload.
      if (reduce && ctx) {
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(starCanvas, 0, 0);
      }
    }
    function onPointerMove(e: PointerEvent) {
      mx = e.clientX;
      my = e.clientY;
    }
    function onPointerLeave() {
      mx = -9999;
      my = -9999;
    }
    function onVisibility() {
      visible = !document.hidden;
      if (visible && !reduce) kick();
    }

    resize();

    if (reduce) {
      // still frame: starfield only, no animation loop, no reactive network
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(starCanvas, 0, 0);
    } else {
      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerleave", onPointerLeave);
      document.addEventListener("visibilitychange", onVisibility);
      kick();
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
      document.removeEventListener("visibilitychange", onVisibility);
      nodes = [];
    };
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 block"
        style={{ zIndex: "var(--z-cosmos)" }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0"
        style={{
          zIndex: "var(--z-vignette)",
          background:
            "radial-gradient(120% 110% at 50% 45%, transparent 52%, rgba(4,4,8,0.7))",
        }}
      />
    </>
  );
}
