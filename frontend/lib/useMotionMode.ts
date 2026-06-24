"use client";

// React access to the resolved motion mode. The data-motion attribute on <html>
// is the single source of truth, so this hook reads it and subscribes to the
// events that change it. SSR-safe: the server snapshot is "full" and
// useSyncExternalStore reconciles to the real value after hydration.

import { useSyncExternalStore } from "react";
import {
  COMPACT_MOTION_QUERY,
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
  // The compact query feeds rung 3. Crossing its boundary (a resize across
  // 1024px, a rotation) re-resolves the mode like an OS change, so a visitor who
  // never chose flips between quiet and full as the viewport class changes.
  const compactMq = window.matchMedia(COMPACT_MOTION_QUERY);
  // Sync the attribute before notifying. syncMotionFromSystem early-returns on a
  // stored choice, so an OS or device-class change only moves an unset mode.
  const onSystem = () => {
    syncMotionFromSystem();
    onChange();
  };
  mq.addEventListener("change", onSystem);
  compactMq.addEventListener("change", onSystem);
  window.addEventListener(MOTION_EVENT, onChange);
  // A choice made in another tab arrives as a storage event. Ignore writes to
  // other keys, but a null key (a full clear) counts as a reset.
  const onStorage = (event: StorageEvent) => {
    if (event.key !== null && event.key !== MOTION_STORAGE_KEY) return;
    syncMotionFromStorage();
    onChange();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    mq.removeEventListener("change", onSystem);
    compactMq.removeEventListener("change", onSystem);
    window.removeEventListener(MOTION_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function useMotionMode(): MotionMode {
  return useSyncExternalStore(subscribe, readMotionMode, () => "full");
}
