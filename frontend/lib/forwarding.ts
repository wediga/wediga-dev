// Forward the visitor's session cookie to the backend verbatim, never
// re-serialized, because re-encoding (cookies().toString()) re-encodes the
// signed session value and the backend then rejects it. Takes the raw header
// string rather than reading it, since the BFF route handlers and the
// server-side reads source the cookie differently.
export function sessionCookieHeader(
  cookie: string | null | undefined,
): Record<string, string> {
  return cookie ? { cookie } : {};
}
