import { redirect } from "next/navigation";
import { cookies } from "next/headers";

import { backendUrl } from "@/lib/backend";

// Server-side guard for the recruiter views (portfolio, CV, contact). It asks
// the backend whether the forwarded session is a recruiter or admin session.
// Without one the visitor is sent to the landing page, so these pages never
// render for someone who has not redeemed a valid link.
export default async function RecruiterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(backendUrl("/recruiter/session"), {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });
  if (!response.ok) {
    redirect("/");
  }

  return <>{children}</>;
}
