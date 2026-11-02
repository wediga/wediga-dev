import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// The admin reads the latest sync and the repos it saw from the admin-only
// backend endpoint.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/github/admin/repos");
}
