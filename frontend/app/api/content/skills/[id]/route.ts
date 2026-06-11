import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

type Params = { params: Promise<{ id: string }> };

export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(request, `/content/skills/${encodeURIComponent(id)}`);
}

export async function DELETE(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(request, `/content/skills/${encodeURIComponent(id)}`);
}
