import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "@/lib/backend";

// The CV download is binary, so it cannot go through the text-based proxy. This
// forwards the visitor's session cookie to the recruiter-gated backend endpoint
// and streams the bytes back unchanged.
export async function GET(request: NextRequest) {
  const headers: Record<string, string> = {};
  const cookie = request.headers.get("cookie");
  if (cookie) headers["cookie"] = cookie;

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
  return new NextResponse(body, {
    status: 200,
    headers: {
      "content-type": "application/pdf",
      "content-disposition":
        backendResponse.headers.get("content-disposition") ??
        'attachment; filename="Lebenslauf.pdf"',
      "cache-control": "private, no-store",
      // Never let a polyglot upload be sniffed as HTML, and give the PDF no
      // capabilities of its own, so the inline preview can carry no XSS.
      "x-content-type-options": "nosniff",
      "content-security-policy": "default-src 'none'",
    },
  });
}
