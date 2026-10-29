import LoginForm from "@/components/LoginForm";
import { AUTHENTIK_ADMIN_LOGIN } from "@/lib/authRedirect";
import { backendUrl } from "@/lib/backend";

// Offers the login through authentik only while the backend has it switched
// on. If the backend cannot tell, the password login stands alone.
export default async function LoginPage() {
  const response = await fetch(backendUrl("/auth/oidc/status"), {
    cache: "no-store",
  });
  const enabled =
    response.ok && ((await response.json()) as { enabled: boolean }).enabled;

  return (
    <LoginForm authentikLoginHref={enabled ? AUTHENTIK_ADMIN_LOGIN : null} />
  );
}
