import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "@/lib/backend";

// Magic-link entry point. A recruiter opens /r/{token}, this handler redeems the
// token at the backend server-side, sets the recruiter session cookie and
// redirects to the landing page. A route handler, not a page, because only a
// route handler may set cookies. The landing then sees the fresh session and
// offers the door into the portfolio, so a recruiter enters through the hero
// like everyone else. An invalid, expired or revoked token redirects to a
// generic error page without revealing which of the three it was.
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

  // Relative redirects: the browser resolves them against the public URL in the
  // address bar. Building an absolute URL from request.url would use the internal
  // bind host (0.0.0.0:3000) behind the reverse proxy and send the recruiter there.
  if (!backendResponse.ok) {
    return new NextResponse(null, {
      status: 303,
      headers: { Location: "/link-invalid" },
    });
  }

  const response = new NextResponse(null, {
    status: 303,
    headers: { Location: "/" },
  });
  for (const value of backendResponse.headers.getSetCookie()) {
    response.headers.append("set-cookie", value);
  }
  return response;
}
