import { NextResponse } from "next/server";

// BFF route handler placeholder. Later this proxies the backend healthcheck.
// The browser never reaches the backend directly, only this route does.
export async function GET() {
  return NextResponse.json({ status: "ok", service: "frontend-bff" });
}
