import { NextRequest } from "next/server";
import { proxyToBackend, type Params } from "@/lib/bff";

export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(request, `/content/projects/${encodeURIComponent(id)}`);
}

export async function DELETE(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyToBackend(request, `/content/projects/${encodeURIComponent(id)}`);
}
