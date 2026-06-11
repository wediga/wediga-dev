import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/bff";

// The admin editor needs the full record, so the GET maps to the admin read.
// The public page reads name and email through the server data layer instead.
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/content/admin/impressum");
}

export async function PUT(request: NextRequest) {
  return proxyToBackend(request, "/content/impressum");
}

export async function DELETE(request: NextRequest) {
  return proxyToBackend(request, "/content/impressum");
}
