import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "./backend";
import { sessionCookieHeader } from "./forwarding";

// The login through authentik runs in the backend. The route handlers under
// /auth only pass the browser's request on, with its query string and session
// cookie, and hand the backend's redirect and session cookie back, like
// /r/{token}. Anything but a redirect (a failed login, or 404 while the login
// is switched off) sends the browser to the password login. The cookie is
// relayed then as well, so a used login state never stays behind.
const SEE_OTHER = 303;
const FALLBACK = "/login";

// Starts the login through authentik and comes back to the admin area.
export const AUTHENTIK_ADMIN_LOGIN = "/auth/login?next=/admin";

export async function relayLoginRedirect(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  const backendResponse = await fetch(
    backendUrl(`${backendPath}${request.nextUrl.search}`),
    {
      headers: sessionCookieHeader(request.headers.get("cookie")),
      cache: "no-store",
      redirect: "manual",
    },
  );
  const location = backendResponse.headers.get("location");
  const target =
    backendResponse.status === SEE_OTHER && location ? location : FALLBACK;

  const response = new NextResponse(null, {
    status: SEE_OTHER,
    headers: { Location: target },
  });

  for (const value of backendResponse.headers.getSetCookie()) {
    response.headers.append("set-cookie", value);
  }

  return response;
}
