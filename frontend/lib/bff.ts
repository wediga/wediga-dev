import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "./backend";
import { sessionCookieHeader } from "./forwarding";

// Route params for the dynamic [id] handlers. Next.js passes params as a
// promise, so each handler awaits it before reading the id.
export type Params = { params: Promise<{ id: string }> };

// Forward a browser request to the backend and relay the response back. The
// incoming session cookie and CSRF header travel to the backend unchanged, and
// each Set-Cookie the backend returns is appended one by one via getSetCookie(),
// which keeps every cookie's attributes intact instead of folding them into one
// comma-joined header.
export async function proxyToBackend(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  const method = request.method;
  const headers: Record<string, string> = {};

  Object.assign(headers, sessionCookieHeader(request.headers.get("cookie")));

  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;

  // Carry the real client IP through, so the login rate limit keys on the
  // visitor and not the single frontend container. Caddy sets this header,
  // locally it is absent and the backend falls back to the peer.
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

// A multipart upload cannot go through the JSON proxy, so this forwards the
// session cookie, the CSRF token and the raw multipart body (boundary intact)
// to an admin-gated backend endpoint. The file cap lives on the backend,
// maxBytes covers the multipart envelope around it, so the BFF rejects an
// oversized body up front instead of buffering it whole in the frontend process.
export async function forwardUpload(
  request: NextRequest,
  backendPath: string,
  maxBytes: number,
): Promise<NextResponse> {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > maxBytes) {
    return new NextResponse("Payload too large", { status: 413 });
  }

  const headers: Record<string, string> = {};
  Object.assign(headers, sessionCookieHeader(request.headers.get("cookie")));
  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  const body = await request.arrayBuffer();
  const backendResponse = await fetch(backendUrl(backendPath), {
    method: "POST",
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
  });

  const text = await backendResponse.text();
  const response = new NextResponse(text, { status: backendResponse.status });
  const responseType = backendResponse.headers.get("content-type");
  if (responseType) response.headers.set("content-type", responseType);
  return response;
}

// A binary download cannot go through the text-based proxy, so this forwards the
// session cookie and the query string to the backend endpoint and streams the
// bytes back unchanged.
export async function relayFile(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  const headers = sessionCookieHeader(request.headers.get("cookie"));

  const backendResponse = await fetch(
    backendUrl(`${backendPath}${request.nextUrl.search}`),
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

  // The file security headers (content-type, content-disposition, cache-control,
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
