import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "@/lib/backend";

// Magic-link entry point. A recruiter opens /r/{token}; this route handler
// redeems the token at the backend server-side, passes the recruiter session
// cookie back to the browser and redirects onto the landing page. A route
// handler is used (not a page) because only a route handler may set cookies.
// The landing then sees the fresh recruiter session and offers the door into the
// portfolio, so a recruiter enters through the hero like everyone else instead
// of being dropped straight into the portfolio. The redeem, the cookie and the
// CSRF protection are unchanged; only the redirect target moved from /portfolio
// to /. An invalid, expired or revoked token still lands on a friendly error
// page without revealing which of the three it was.
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ token: string }> },
) {
  const { token } = await params;

  const headers: Record<string, string> = {};
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers["x-forwarded-for"] = forwardedFor;

  const backendResponse = await fetch(
    backendUrl(`/recruiter/redeem/${encodeURIComponent(token)}`),
    { method: "POST", headers, cache: "no-store", redirect: "manual" },
  );

  if (!backendResponse.ok) {
    return NextResponse.redirect(new URL("/link-invalid", request.url));
  }

  const response = NextResponse.redirect(new URL("/", request.url));
  for (const value of backendResponse.headers.getSetCookie()) {
    response.headers.append("set-cookie", value);
  }
  return response;
}
