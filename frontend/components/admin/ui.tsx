"use client";

// The shared admin design system. One small set of primitives the eight
// maintenance pages build on, so every form looks and behaves the same: the
// same input, the same three button weights, the same per-action feedback, and
// the same inline confirmation before a destructive write. Everything is dark
// and drawn from the central Sakura tokens in globals.css; the generative hero
// accents of the recruiter views are deliberately not used here.

import {
  type ButtonHTMLAttributes,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

// One status per write action. Pages key these by action (e.g. "save",
// "delete-12") so each control reports its own outcome instead of sharing a
// single page-wide string.
export type ActionStatus =
  | { state: "idle" }
  | { state: "pending" }
  | { state: "success"; message: string }
  | { state: "error"; message: string };

const IDLE: ActionStatus = { state: "idle" };

// Drives the per-action feedback. run() flips the keyed status to pending,
// awaits the write, then settles on success or error; success fades back to
// idle on its own so the form rests quietly, errors stay until the next try.
// set() is for non-write feedback such as a failed initial load.
export function useActionFeedback() {
  const [map, setMap] = useState<Record<string, ActionStatus>>({});
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  useEffect(() => {
    const pending = timers.current;
    return () => {
      Object.values(pending).forEach(clearTimeout);
    };
  }, []);

  const set = useCallback((key: string, status: ActionStatus) => {
    setMap((current) => ({ ...current, [key]: status }));
  }, []);

  const run = useCallback(
    async (
      key: string,
      action: () => Promise<boolean>,
      messages: { success: string; error: string },
    ): Promise<boolean> => {
      const timer = timers.current[key];
      if (timer) {
        clearTimeout(timer);
        delete timers.current[key];
      }
      setMap((current) => ({ ...current, [key]: { state: "pending" } }));

      let ok = false;
      try {
        ok = await action();
      } catch {
        ok = false;
      }

      setMap((current) => ({
        ...current,
        [key]: ok
          ? { state: "success", message: messages.success }
          : { state: "error", message: messages.error },
      }));

      if (ok) {
        timers.current[key] = setTimeout(() => {
          setMap((current) => ({ ...current, [key]: IDLE }));
          delete timers.current[key];
        }, 2600);
      }
      return ok;
    },
    [],
  );

  const get = useCallback(
    (key: string): ActionStatus => map[key] ?? IDLE,
    [map],
  );

  return { run, get, set };
}

// Inline feedback anchored next to the action that produced it. Announced to
// assistive tech, and never colour-only: the word carries the meaning, the
// colour reinforces it.
export function Feedback({
  status,
  pendingLabel = "Saving…",
  className = "",
}: {
  status: ActionStatus;
  pendingLabel?: string;
  className?: string;
}) {
  if (status.state === "idle") return null;
  const tone =
    status.state === "success"
      ? "text-success"
      : status.state === "error"
        ? "text-danger"
        : "text-muted";
  const text =
    status.state === "pending"
      ? pendingLabel
      : status.message;
  return (
    <span
      role="status"
      aria-live="polite"
      className={`text-xs font-medium ${tone} ${className}`}
    >
      {text}
    </span>
  );
}

// One input look shared by AdminField and the few inline edit fields (skills,
// repos), so the form controls cannot drift apart. Width is set per use. Focus
// uses the same crimson outline idiom as the login and recruiter surfaces.
export const ADMIN_INPUT =
  "rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted transition-colors duration-150 ease-out hover:border-muted-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 disabled:cursor-not-allowed disabled:opacity-60";

type Variant = "primary" | "secondary" | "danger" | "danger-solid";

const VARIANTS: Record<Variant, string> = {
  // Crimson accent carries the one primary write per block.
  primary: "bg-accent text-bg hover:bg-accent/90",
  secondary:
    "border border-line bg-transparent text-ink hover:border-muted-2 hover:bg-surface",
  // Outline danger for the first click of a destructive action…
  danger: "border border-danger/50 bg-transparent text-danger hover:bg-danger/10",
  // …solid danger once it is confirmed, so the committed step reads heavier.
  "danger-solid": "bg-danger text-bg hover:bg-danger/90",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  pending?: boolean;
  pendingLabel?: string;
};

export function AdminButton({
  variant = "secondary",
  pending = false,
  pendingLabel,
  disabled,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || pending}
      aria-busy={pending || undefined}
      className={`quiet-press inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 disabled:pointer-events-none disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {pending && pendingLabel ? pendingLabel : children}
    </button>
  );
}

type FieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  hint?: string;
  multiline?: boolean;
  rows?: number;
  mono?: boolean;
  className?: string;
};

// Label above the control, optional hint below it, never a placeholder standing
// in for the label. Errors are reported per action by the Feedback component,
// anchored at the button that triggered the write, not inline on the field.
export function AdminField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  hint,
  multiline = false,
  rows = 4,
  mono = false,
  className = "",
}: FieldProps) {
  const fieldId = useId();
  const control = `${ADMIN_INPUT} w-full ${mono ? "font-mono" : ""}`;

  return (
    <div className={className}>
      <label
        htmlFor={fieldId}
        className="mb-1.5 block text-[0.8125rem] font-medium text-muted"
      >
        {label}
      </label>
      {multiline ? (
        <textarea
          id={fieldId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={rows}
          placeholder={placeholder}
          aria-describedby={hint ? `${fieldId}-hint` : undefined}
          className={`${control} resize-y leading-relaxed`}
        />
      ) : (
        <input
          id={fieldId}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          aria-describedby={hint ? `${fieldId}-hint` : undefined}
          className={control}
        />
      )}
      {hint ? (
        <p id={`${fieldId}-hint`} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

// A teaching empty state: it says what is missing and where to add the first
// item, rather than just "nothing here".
export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-sm border border-dashed border-line px-4 py-6 text-center text-sm text-muted">
      {children}
    </p>
  );
}

// Two-step destructive confirmation, kept in the DOM rather than a native
// window.confirm: the first click arms it, a clear prompt plus a heavier
// confirm and a cancel appear in place, and only the second click sends. This
// is presentation around the existing write; it never changes the request.
export function ConfirmButton({
  label,
  prompt,
  confirmLabel = "Confirm",
  pendingLabel,
  onConfirm,
  pending = false,
  disabled = false,
}: {
  label: string;
  prompt: string;
  confirmLabel?: string;
  pendingLabel?: string;
  onConfirm: () => unknown;
  pending?: boolean;
  disabled?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);

  if (!confirming) {
    return (
      <AdminButton
        variant="danger"
        disabled={disabled}
        onClick={() => setConfirming(true)}
      >
        {label}
      </AdminButton>
    );
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted">{prompt}</span>
      <AdminButton
        variant="danger-solid"
        pending={pending}
        pendingLabel={pendingLabel}
        onClick={async () => {
          await onConfirm();
          setConfirming(false);
        }}
      >
        {confirmLabel}
      </AdminButton>
      <AdminButton variant="secondary" onClick={() => setConfirming(false)}>
        Cancel
      </AdminButton>
    </span>
  );
}
