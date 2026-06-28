// Map a project's free-text status onto one of the three semantic status
// colours. The status is admin-entered, so the match is tolerant across the
// German and common English labels, and anything unrecognised falls back to
// neutral (muted text), so a new label never renders the wrong colour.

export type StatusKind = "done" | "wip" | "early" | "neutral";

export function statusKind(status: string | null | undefined): StatusKind {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  // Order matters: "early development" must read as early, not in-progress, so
  // the early check runs before the generic development check.
  if (/(fertig|abgeschlossen|done|complete|released|live|stable)/.test(s)) {
    return "done";
  }
  if (/(früh|fruh|early|konzept|concept|geplant|planned|idee|idea)/.test(s)) {
    return "early";
  }
  if (/(entwicklung|progress|wip|laufend|beta|aktiv|active)/.test(s)) {
    return "wip";
  }
  return "neutral";
}

// The token class per status kind. Neutral stays muted, never coloured.
export const STATUS_CLASS: Record<StatusKind, string> = {
  done: "text-status-done",
  wip: "text-status-wip",
  early: "text-status-early",
  neutral: "text-muted-2",
};
