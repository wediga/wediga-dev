import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// Admin-only: revoke a link, which blocks any further redeem of its token.
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyToBackend(request, `/recruiter/links/${encodeURIComponent(id)}/revoke`);
}
