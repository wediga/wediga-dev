"use client";

// React access to the resolved motion mode. The data-motion attribute on <html>
// (set before paint by the init script, updated by the switch and by live OS
// changes) is the single source of truth, so this hook just reads it and
// subscribes to the events that change it. SSR-safe: the server snapshot is
// "full", and useSyncExternalStore reconciles to the real value right after
// hydration without a mismatch.

import { useSyncExternalStore } from "react";
import {
  MOTION_EVENT,
  MOTION_STORAGE_KEY,
  REDUCED_MOTION_QUERY,
  readMotionMode,
  syncMotionFromStorage,
  syncMotionFromSystem,
  type MotionMode,
} from "./motion";

function subscribe(onChange: () => void): () => void {
  const mq = window.matchMedia(REDUCED_MOTION_QUERY);
  // An OS change only moves the mode when no deliberate choice is stored; sync the
  // attribute first, then notify.
  const onSystem = () => {
    syncMotionFromSystem();
    onChange();
  };
  mq.addEventListener("change", onSystem);
  window.addEventListener(MOTION_EVENT, onChange);
  // A choice made in another tab reaches us as a storage event; catch this tab's
  // attribute up to the new stored value, then notify. Ignore writes to other
  // keys (e.key is null on a full clear, which we do treat as a reset).
  const onStorage = (event: StorageEvent) => {
    if (event.key !== null && event.key !== MOTION_STORAGE_KEY) return;
    syncMotionFromStorage();
    onChange();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    mq.removeEventListener("change", onSystem);
    window.removeEventListener(MOTION_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function useMotionMode(): MotionMode {
  return useSyncExternalStore(subscribe, readMotionMode, () => "full");
}
