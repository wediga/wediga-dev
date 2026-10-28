import { NextRequest } from "next/server";
import { relayLoginRedirect } from "@/lib/authRedirect";

// The redirect URI that authentik sends the browser back to with the code.
export async function GET(request: NextRequest) {
  return relayLoginRedirect(request, "/auth/oidc/callback");
}
