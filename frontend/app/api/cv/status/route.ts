import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// Whether a CV PDF is currently stored. Plain JSON, so the text proxy fits; the
// backend applies the recruiter-or-admin gate against the forwarded session.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/cv/status");
}
