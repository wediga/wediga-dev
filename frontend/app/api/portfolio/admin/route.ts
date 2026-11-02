import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// The admin reads every synced repo with its portfolio entry.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/portfolio/admin");
}
