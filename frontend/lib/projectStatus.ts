// The colour of each project status, by the keys the backend migration writes
// into ``project_status`` (a backend test compares both). The labels come from
// the backend. An archived repo shows as archived whatever its status, in the
// neutral colour.

export const STATUS_CLASS = {
  done: "text-status-done",
  wip: "text-status-wip",
  early: "text-status-early",
  stopped: "text-muted-2",
} as const;

export type StatusKey = keyof typeof STATUS_CLASS;

export const ARCHIVED = { label: "Archiviert", className: "text-muted-2" };
