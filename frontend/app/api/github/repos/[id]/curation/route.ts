import { NextRequest } from "next/server";
import { proxyToBackend, type Params } from "@/lib/bff";

export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(
    request,
    `/github/repos/${encodeURIComponent(id)}/curation`,
  );
}
