import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// Admin-only: list links with their call statistics, and create a new link.
// Both forward the admin session and (for the create) the CSRF token to the
// backend, which enforces the admin gate.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/recruiter/links");
}

export async function POST(request: NextRequest) {
  return proxyToBackend(request, "/recruiter/links");
}
