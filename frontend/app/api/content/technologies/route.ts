import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/content/technologies");
}

export async function POST(request: NextRequest) {
  return proxyToBackend(request, "/content/technologies");
}
