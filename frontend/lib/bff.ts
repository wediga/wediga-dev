import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "./backend";
import { sessionCookieHeader } from "./forwarding";

// Route params for the dynamic [id] handlers. Next.js passes params as a
// promise, so each handler awaits it before reading the id.
export type Params = { params: Promise<{ id: string }> };

// Forward a browser request to the backend and relay the response back.
// The incoming session cookie and the CSRF header travel to the backend, and
// every Set-Cookie the backend returns is passed back to the browser one by
// one via getSetCookie(), which keeps each cookie's attributes intact instead
// of folding them into a single comma-joined header.
export async function proxyToBackend(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  const method = request.method;
  const headers: Record<string, string> = {};

  Object.assign(headers, sessionCookieHeader(request.headers.get("cookie")));

  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;

  // Carry the real client IP through to the backend, so the login rate limit
  // keys on the visitor and not on the single frontend container. Caddy sets
  // this header; locally it is absent and the backend falls back to the peer.
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers["x-forwarded-for"] = forwardedFor;

  let body: string | undefined;
  if (method !== "GET" && method !== "HEAD") {
    const text = await request.text();
    if (text) {
      body = text;
      headers["content-type"] = "application/json";
    }
  }

  const backendResponse = await fetch(backendUrl(backendPath), {
    method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
  });

  const responseBody = await backendResponse.text();
  const response = new NextResponse(responseBody, {
    status: backendResponse.status,
  });

  const contentType = backendResponse.headers.get("content-type");
  if (contentType) response.headers.set("content-type", contentType);

  for (const value of backendResponse.headers.getSetCookie()) {
    response.headers.append("set-cookie", value);
  }

  return response;
}
