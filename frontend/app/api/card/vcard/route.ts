import { NextRequest } from "next/server";
import { relayFile } from "@/lib/bff";

export async function GET(request: NextRequest) {
  return relayFile(request, "/card/vcard");
}
