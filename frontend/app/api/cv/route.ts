import { NextRequest } from "next/server";
import { forwardUpload } from "@/lib/bff";

// The 10 MB file cap lives on the backend, this bound covers the multipart
// envelope around it.
const MAX_UPLOAD_BYTES = 12 * 1024 * 1024;

export async function POST(request: NextRequest) {
  return forwardUpload(request, "/cv", MAX_UPLOAD_BYTES);
}
