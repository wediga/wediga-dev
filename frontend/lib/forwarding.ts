// Forward the visitor's session cookie to the backend verbatim. The raw cookie
// header value is passed through unchanged, never re-serialized, because
// re-encoding (cookies().toString()) would re-encode the signed session value
// and the backend would then reject it. Used by both the BFF route handlers and
// the server-side reads, which source the cookie differently, so this takes the
// raw string instead of fetching it itself.
export function sessionCookieHeader(
  cookie: string | null | undefined,
): Record<string, string> {
  return cookie ? { cookie } : {};
}
