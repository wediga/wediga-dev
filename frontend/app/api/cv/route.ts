import { NextRequest, NextResponse } from "next/server";
import { backendUrl } from "@/lib/backend";
import { sessionCookieHeader } from "@/lib/forwarding";

// The 10 MB file cap lives on the backend, this bound covers the multipart
// envelope around it, so the BFF rejects an oversized body up front instead of
// buffering it whole in the frontend process.
const MAX_UPLOAD_BYTES = 12 * 1024 * 1024;

// A multipart upload cannot go through the JSON proxy, so this forwards the
// session cookie, the CSRF token and the raw multipart body (boundary intact)
// to the admin-gated backend endpoint.
export async function POST(request: NextRequest) {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > MAX_UPLOAD_BYTES) {
    return new NextResponse("Payload too large", { status: 413 });
  }

  const headers: Record<string, string> = {};
  Object.assign(headers, sessionCookieHeader(request.headers.get("cookie")));
  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  const body = await request.arrayBuffer();
  const backendResponse = await fetch(backendUrl("/cv"), {
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
