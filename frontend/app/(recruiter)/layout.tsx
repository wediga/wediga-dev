import { redirect } from "next/navigation";
import { headers } from "next/headers";

import { backendUrl } from "@/lib/backend";
import { RecruiterShell } from "@/components/recruiter/RecruiterShell";

// Server-side guard for the recruiter views (portfolio, CV, contact): ask the
// backend whether the forwarded session is a recruiter or admin session, send
// the visitor to the landing page otherwise. The raw cookie header is forwarded
// verbatim (the BFF route handlers do the same) because re-serializing via
// cookies().toString() re-encodes the signed session value and the backend
// then rejects it.
export default async function RecruiterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieHeader = (await headers()).get("cookie");
  const response = await fetch(backendUrl("/recruiter/session"), {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });
  if (!response.ok) {
    redirect("/");
  }

  return <RecruiterShell>{children}</RecruiterShell>;
}
