// Map a project's free-text status onto one of the three fixed semantic status
// colours. The status string is admin-entered, so the match is tolerant: it
// reads the German labels the admin uses today and the common English ones, and
// anything unrecognised falls back to neutral (no colour, just muted text), so a
// new label never renders as a wrong-meaning colour.

export type StatusKind = "done" | "wip" | "early" | "neutral";

export function statusKind(status: string | null | undefined): StatusKind {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  // Order matters: "frühe Entwicklung" must read as early, not as in-progress,
  // so the early check runs before the generic development check.
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

// The token class for each status kind. Neutral stays muted, never coloured.
export const STATUS_CLASS: Record<StatusKind, string> = {
  done: "text-status-done",
  wip: "text-status-wip",
  early: "text-status-early",
  neutral: "text-muted-2",
};
