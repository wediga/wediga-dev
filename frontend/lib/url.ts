// Return the value only when it is an http(s) URL, otherwise undefined, so a
// stored or mirrored link can never carry a javascript: or data: scheme into an
// anchor href. The backend validates links on write, this is a second line at
// render time, in particular for the GitHub-mirrored repo url, which is foreign
// data.
export function safeHref(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  const lower = trimmed.toLowerCase();
  if (lower.startsWith("https://") || lower.startsWith("http://")) {
    return trimmed;
  }
  return undefined;
}
