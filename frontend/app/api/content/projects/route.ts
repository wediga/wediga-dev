import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// The admin list needs every project including hidden ones, so GET maps to the
// admin-only backend endpoint. The public views read visible projects through
// the server data layer instead.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/content/admin/projects");
}

export async function POST(request: NextRequest) {
  return proxyToBackend(request, "/content/projects");
}
