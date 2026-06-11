// Return the value only when it is a safe http(s) URL, otherwise undefined, so
// a stored or mirrored link can never carry a javascript: or data: scheme into
// an anchor href. The backend already validates links on write; this is a
// second line at render time, in particular for the repo url mirrored from
// GitHub, which is foreign data.
export function safeHref(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  const lower = trimmed.toLowerCase();
  if (lower.startsWith("https://") || lower.startsWith("http://")) {
    return trimmed;
  }
  return undefined;
}
