import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/content/about");
}

export async function PUT(request: NextRequest) {
  return proxyToBackend(request, "/content/about");
}

export async function DELETE(request: NextRequest) {
  return proxyToBackend(request, "/content/about");
}
