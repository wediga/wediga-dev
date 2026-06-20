"use client";

import { useRouter } from "next/navigation";
import { AdminButton } from "@/components/admin/ui";

export function LogoutButton() {
  const router = useRouter();

  async function logout() {
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
