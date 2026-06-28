import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// Whether a CV PDF is stored. Plain JSON, so the text proxy fits, and the
// backend applies the recruiter-or-admin gate against the forwarded session.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/cv/status");
}
