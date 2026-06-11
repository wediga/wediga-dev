import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// The admin list needs every repo with its mirrored and curation fields, so
// the GET maps to the admin-only backend endpoint. The recruiter view reads
// the curated list through the server data layer instead.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/github/admin/repos");
}
