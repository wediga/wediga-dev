import { NextRequest } from "next/server";
import { forwardUpload, relayFile } from "@/lib/bff";

// The 5 MB file cap lives on the backend, this bound covers the multipart
// envelope around it.
const MAX_UPLOAD_BYTES = 6 * 1024 * 1024;

export async function GET(request: NextRequest) {
  return relayFile(request, "/portrait");
}

export async function POST(request: NextRequest) {
  return forwardUpload(request, "/portrait", MAX_UPLOAD_BYTES);
}
