import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "@/lib/backend";
import { sessionCookieHeader } from "@/lib/forwarding";

// A binary download cannot go through the text-based proxy, so this forwards the
// session cookie to the recruiter-gated backend endpoint and streams the bytes
// back unchanged.
export async function GET(request: NextRequest) {
  const headers = sessionCookieHeader(request.headers.get("cookie"));

  // Carry the query string through, so the ?inline switch reaches the backend:
  // the CV page embeds a preview while the download link forces a save.
  const backendResponse = await fetch(
    backendUrl(`/cv/download${request.nextUrl.search}`),
    {
      headers,
      cache: "no-store",
      redirect: "manual",
    },
  );

  if (!backendResponse.ok) {
    return new NextResponse(null, { status: backendResponse.status });
  }

  const body = await backendResponse.arrayBuffer();
  const response = new NextResponse(body, { status: 200 });

  // The PDF security headers (content-type, content-disposition, cache-control,
  // x-content-type-options, content-security-policy) are authoritative on the
  // backend and asserted by the backend tests. Relay them so the values live in
  // one place instead of being hardcoded again here.
  for (const name of [
    "content-type",
    "content-disposition",
    "cache-control",
    "x-content-type-options",
    "content-security-policy",
  ]) {
    const value = backendResponse.headers.get(name);
    if (value) response.headers.set(name, value);
  }

  return response;
}
