import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "./backend";

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

  const cookie = request.headers.get("cookie");
  if (cookie) headers["cookie"] = cookie;

  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;

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
