import { NextRequest } from "next/server";
import { proxyToBackend, type Params } from "@/lib/bff";

// Admin-only: replace the expiry of a link, null removes it.
export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(request, `/recruiter/links/${encodeURIComponent(id)}/expiry`);
}
