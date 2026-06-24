import { NextResponse } from "next/server";

// Liveness probe for the frontend BFF. Returns a fixed ok without touching the
// backend, so it reports only that this process is up.
export async function GET() {
  return NextResponse.json({ status: "ok", service: "frontend-bff" });
}
