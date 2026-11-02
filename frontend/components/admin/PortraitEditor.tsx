"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { apiWrite, getCsrfToken } from "@/lib/adminClient";
import {
  FOCUS_MAX,
  PORTRAIT_SRC,
  PORTRAIT_TYPES,
  ZOOM_MAX,
  ZOOM_MIN,
  type PortraitCrop,
} from "@/lib/portrait";
import { AdminButton, Feedback, useActionFeedback } from "@/components/admin/ui";
import { Portrait } from "@/components/Portrait";

const CROP_SRC = `${PORTRAIT_SRC}/crop`;
const UPLOAD_FAILED = "Upload failed. Try again.";

// How far one arrow key moves the focus and one slider step the zoom, in
// percent. Moving the image left brings more of its right side into view, so
// the focus moves right.
const KEY_STEP = 2;
const ZOOM_STEP = 5;
const KEY_MOVES: Record<string, { x: number; y: number }> = {
  ArrowLeft: { x: KEY_STEP, y: 0 },
  ArrowRight: { x: -KEY_STEP, y: 0 },
  ArrowUp: { x: 0, y: KEY_STEP },
  ArrowDown: { x: 0, y: -KEY_STEP },
};

type Drag = { x: number; y: number; crop: PortraitCrop };
type CropChange = (crop: PortraitCrop) => void;

function clampFocus(value: number): number {
  return Math.min(FOCUS_MAX, Math.max(0, Math.round(value)));
}

function shifted(crop: PortraitCrop, by: { x: number; y: number }): PortraitCrop {
  return { ...crop, x: clampFocus(crop.x + by.x), y: clampFocus(crop.y + by.y) };
}

// Dragging the image by a whole crop width moves the focus across the image,
// against the direction of the drag.
function dragged(start: Drag, event: PointerEvent<HTMLElement>): PortraitCrop {
  const box = event.currentTarget.getBoundingClientRect();

  return shifted(start.crop, {
    x: ((start.x - event.clientX) / box.width) * FOCUS_MAX,
    y: ((start.y - event.clientY) / box.height) * FOCUS_MAX,
  });
}

function uploadError(status: number): string {
  if (status === 413) {
    return "The file is too large.";
  }

  if (status === 415 || status === 422) {
    return "Only a JPEG, PNG or WebP image is accepted.";
  }

  return UPLOAD_FAILED;
}

// Upload an image and return the crop it starts with, or the message to show.
async function sendPortrait(file: File): Promise<PortraitCrop | string> {
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(PORTRAIT_SRC, {
      method: "POST",
      headers: { "X-CSRF-Token": await getCsrfToken() },
      body: form,
    });

    if (!response.ok) {
      return uploadError(response.status);
    }

    return (await response.json()) as PortraitCrop;
  } catch {
    return UPLOAD_FAILED;
  }
}

// Pointer and arrow key handlers that move the focus of the crop.
function useDragFocus(crop: PortraitCrop, onChange: CropChange) {
  const drag = useRef<Drag | null>(null);

  return {
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { x: event.clientX, y: event.clientY, crop };
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      if (drag.current) onChange(dragged(drag.current, event));
    },
    onPointerUp: () => {
      drag.current = null;
    },
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
      const step = KEY_MOVES[event.key];

      if (!step) return;

      event.preventDefault();
      onChange(shifted(crop, step));
    },
  };
}

// The round crop is how the landing page shows the portrait, the tall one is
// close to how a phone shows a contact. The round one is the handle.
function PortraitPreviews({ src, crop, onChange }: { src: string; crop: PortraitCrop; onChange: CropChange }) {
  const handlers = useDragFocus(crop, onChange);

  return (
    <div className="flex items-end gap-6">
      <button
        type="button"
        aria-label={`Portrait focus at ${crop.x}% from the left and ${crop.y}% from the top. Drag the image or use the arrow keys.`}
        className="cursor-grab touch-none rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 active:cursor-grabbing"
        {...handlers}
      >
        <Portrait src={src} crop={crop} alt="" className="h-40 w-40 rounded-full" />
      </button>
      <Portrait src={src} crop={crop} alt="" className="h-40 w-28 rounded-md" />
    </div>
  );
}

function ZoomSlider({ crop, onChange }: { crop: PortraitCrop; onChange: CropChange }) {
  return (
    <label className="mt-4 flex max-w-xs flex-col gap-1 text-sm text-muted">
      Zoom {crop.zoom}%
      <input
        type="range"
        min={ZOOM_MIN}
        max={ZOOM_MAX}
        step={ZOOM_STEP}
        value={crop.zoom}
        className="accent-accent"
        onChange={(event) => onChange({ ...crop, zoom: Number(event.target.value) })}
      />
    </label>
  );
}

function CropControls({ src, crop, onChange }: { src: string; crop: PortraitCrop; onChange: CropChange }) {
  const { run, get } = useActionFeedback();
  const save = async () => (await apiWrite(CROP_SRC, "PUT", await getCsrfToken(), crop)).ok;

  return (
    <>
      <div className="mt-4 flex flex-wrap items-end gap-4">
        <PortraitPreviews src={src} crop={crop} onChange={onChange} />
        <AdminButton
          variant="primary"
          pending={get("crop").state === "pending"}
          pendingLabel="Saving…"
          onClick={() => run("crop", save, { success: "Crop saved", error: "Couldn't save the crop. Try again." })}
        >
          Save crop
        </AdminButton>
        <Feedback status={get("crop")} />
      </div>
      <ZoomSlider crop={crop} onChange={onChange} />
    </>
  );
}

function PortraitUpload({ onUploaded }: { onUploaded: CropChange }) {
  const { get, set } = useActionFeedback();

  async function upload(file: File) {
    set("upload", { state: "pending" });
    const result = await sendPortrait(file);

    if (typeof result === "string") {
      set("upload", { state: "error", message: result });

      return;
    }

    onUploaded(result);
    set("upload", { state: "success", message: "Portrait uploaded" });
  }

  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <input
        type="file"
        accept={PORTRAIT_TYPES.join(",")}
        disabled={get("upload").state === "pending"}
        className="text-sm text-muted file:mr-3 file:cursor-pointer file:rounded-sm file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-bg disabled:opacity-60"
        onChange={(event) => {
          const file = event.target.files?.[0];

          if (file) void upload(file);

          event.target.value = "";
        }}
      />
      <Feedback status={get("upload")} pendingLabel="Uploading…" />
    </div>
  );
}

// The portrait and its crop, which every page that shows the image applies.
// The version in the image address changes with every upload, so the
// previews show the new file at once.
export function PortraitEditor() {
  const [crop, setCrop] = useState<PortraitCrop | null>(null);
  const [version, setVersion] = useState(0);
  const { get, set } = useActionFeedback();

  useEffect(() => {
    fetch(CROP_SRC, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((data: PortraitCrop | null) => setCrop(data))
      .catch(() => set("load", { state: "error", message: "Couldn't load the portrait. Reload the page." }));
  }, [set]);

  return (
    <section className="mt-6 rounded-lg border border-line bg-surface/40 p-5 sm:p-6">
      <h2 className="text-sm font-semibold text-ink">Portrait</h2>
      <p className="mt-1 text-sm text-muted">
        Shown on the landing page and on the contact card. Drag and zoom until the crop fits, then save it.
      </p>
      <Feedback status={get("load")} className="mt-3 block" />
      {crop ? <CropControls src={`${PORTRAIT_SRC}?v=${version}`} crop={crop} onChange={setCrop} /> : null}
      <PortraitUpload
        onUploaded={(uploaded) => {
          setCrop(uploaded);
          setVersion((current) => current + 1);
        }}
      />
    </section>
  );
}
