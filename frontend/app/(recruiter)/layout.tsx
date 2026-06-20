import { redirect } from "next/navigation";
import { headers } from "next/headers";

import { backendUrl } from "@/lib/backend";
import { RecruiterShell } from "@/components/recruiter/RecruiterShell";

// Server-side guard for the recruiter views (portfolio, CV, contact). It asks
// the backend whether the forwarded session is a recruiter or admin session.
// Without one the visitor is sent to the landing page, so these pages never
// render for someone who has not redeemed a valid link. The raw cookie header
// is forwarded verbatim, the same way the BFF route handlers do it, because
// re-serializing the cookies (cookies().toString()) re-encodes the signed
// session value and the backend then rejects it.
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
