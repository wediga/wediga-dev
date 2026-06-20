import { redirect } from "next/navigation";
import { headers } from "next/headers";

import { backendUrl } from "@/lib/backend";
import { LogoutButton } from "@/components/LogoutButton";
import { AdminNav } from "@/components/admin/AdminNav";

// Server-side guard: ask the backend whether the forwarded session is an admin
// session. A missing or invalid session redirects to the login page, so the
// admin area is never rendered without authentication. The raw cookie header
// is forwarded verbatim, the same way the BFF route handlers do it, because
// re-serializing the cookies (cookies().toString()) re-encodes the signed
// session value and the backend then rejects it.
export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieHeader = (await headers()).get("cookie");
  const response = await fetch(backendUrl("/auth/me"), {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });
  if (!response.ok) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <header className="sticky top-0 z-[var(--z-nav)] border-b border-line bg-bg/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center justify-between gap-3 px-5 py-3">
          <AdminNav />
          <LogoutButton />
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-5 py-8 sm:py-10">
        {children}
      </main>
    </div>
  );
}
