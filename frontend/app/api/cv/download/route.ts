import { NextRequest } from "next/server";
import { relayFile } from "@/lib/bff";

// The query string travels along, so the ?inline switch reaches the backend:
// the CV page embeds a preview while the download link forces a save.
export async function GET(request: NextRequest) {
  return relayFile(request, "/cv/download");
}
