import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "@/lib/backend";
import { sessionCookieHeader } from "@/lib/forwarding";

// The CV download is binary, so it cannot go through the text-based proxy. This
// forwards the visitor's session cookie to the recruiter-gated backend endpoint
// and streams the bytes back unchanged.
export async function GET(request: NextRequest) {
  const headers = sessionCookieHeader(request.headers.get("cookie"));

  // Carry the query string through, so the ?inline switch reaches the backend
  // and the CV page can embed a preview while the download link forces a save.
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
  // x-content-type-options and content-security-policy) are authoritative on the
  // backend, which the backend tests assert. Relay them here so the values live
  // in one place instead of being hardcoded a second time.
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
