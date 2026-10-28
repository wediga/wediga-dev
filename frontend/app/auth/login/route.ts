import { NextRequest } from "next/server";
import { relayLoginRedirect } from "@/lib/authRedirect";

// Starts the login through authentik, with an optional ?next= target.
export async function GET(request: NextRequest) {
  return relayLoginRedirect(request, "/auth/oidc/login");
}
