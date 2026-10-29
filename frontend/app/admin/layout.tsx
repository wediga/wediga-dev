import { redirect } from "next/navigation";
import { headers } from "next/headers";

import { AUTHENTIK_ADMIN_LOGIN } from "@/lib/authRedirect";
import { backendUrl } from "@/lib/backend";
import { LogoutButton } from "@/components/LogoutButton";
import { AdminNav } from "@/components/admin/AdminNav";

// The backend's answer for a login without the admin role.
const FORBIDDEN = 403;
const NO_ACCESS_PAGE = "/no-access";

// Server-side guard: ask the backend whether the forwarded session is an admin
// session. Without a login the visitor goes to authentik, and while that login
// is switched off, /auth/login falls back to the password login. A login
// without the admin role goes to the no-access page, because authentik would
// return it at once. The raw cookie header is forwarded verbatim (the BFF
// route handlers do the same) because re-serializing via cookies().toString()
// re-encodes the signed session value and the backend then rejects it.
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

  if (response.status === FORBIDDEN) {
    redirect(NO_ACCESS_PAGE);
  }

  if (!response.ok) {
    redirect(AUTHENTIK_ADMIN_LOGIN);
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
