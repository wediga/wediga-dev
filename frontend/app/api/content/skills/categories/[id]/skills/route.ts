import { NextRequest } from "next/server";
import { proxyToBackend, type Params } from "@/lib/bff";

export async function POST(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(
    request,
    `/content/skills/categories/${encodeURIComponent(id)}/skills`,
  );
}
