import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/auth/me");
}
