"use client";

import { useRouter } from "next/navigation";
import { AdminButton } from "@/components/admin/ui";
import { apiWrite } from "@/lib/adminClient";

// The logout through authentik ends the session there as well and returns the
// URL to send the browser to. While that login is switched off its route
// answers 404, and so does a session without a CSRF token, so null means the
// password logout runs as before.
async function authentikLogoutUrl(): Promise<string | null> {
  const csrf = await fetch("/api/csrf", { cache: "no-store" });

  if (!csrf.ok) return null;

  const { csrf_token } = (await csrf.json()) as { csrf_token: string };
  const response = await apiWrite("/api/oidc/logout", "POST", csrf_token);

  if (!response.ok) return null;

  const { redirect } = (await response.json()) as { redirect: string };

  return redirect;
}

export function LogoutButton() {
  const router = useRouter();

  async function logout() {
    const url = await authentikLogoutUrl();

    if (url) {
      window.location.assign(url);
      return;
    }

    await fetch("/api/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <AdminButton variant="secondary" onClick={logout}>
      Logout
    </AdminButton>
  );
}
