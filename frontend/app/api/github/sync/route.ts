import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// The admin "sync now" button posts here. The backend runs the sync behind the
// admin session and CSRF token, and leaves the cache intact on failure.
export async function POST(request: NextRequest) {
  return proxyToBackend(request, "/github/sync");
}
