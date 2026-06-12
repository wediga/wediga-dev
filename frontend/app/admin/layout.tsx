import { redirect } from "next/navigation";
import { headers } from "next/headers";
import Link from "next/link";

import { backendUrl } from "@/lib/backend";
import { LogoutButton } from "@/components/LogoutButton";

const NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/about", label: "About" },
  { href: "/admin/projects", label: "Projects" },
  { href: "/admin/skills", label: "Skills" },
  { href: "/admin/contact", label: "Contact" },
  { href: "/admin/impressum", label: "Impressum" },
  { href: "/admin/repos", label: "Repos" },
  { href: "/admin/cv", label: "CV" },
  { href: "/admin/links", label: "Links" },
];

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
    <div className="min-h-full">
      <header className="flex items-center justify-between border-b border-gray-200 px-6 py-3">
        <nav className="flex flex-wrap gap-4 text-sm">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className="hover:underline">
              {item.label}
            </Link>
          ))}
        </nav>
        <LogoutButton />
      </header>
      <main className="mx-auto max-w-3xl p-6">{children}</main>
    </div>
  );
}
