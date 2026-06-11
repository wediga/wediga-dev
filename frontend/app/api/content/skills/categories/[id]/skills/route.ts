import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

type Params = { params: Promise<{ id: string }> };

export async function POST(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(
    request,
    `/content/skills/categories/${encodeURIComponent(id)}/skills`,
  );
}
