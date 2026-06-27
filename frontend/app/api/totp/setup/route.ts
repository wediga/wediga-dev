import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

export async function POST(request: NextRequest) {
  return proxyToBackend(request, "/auth/totp/setup");
}
