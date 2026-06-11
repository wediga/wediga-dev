// Client-side helpers used by the admin forms. The CSRF token is fetched from
// the BFF once and then sent on every write as the X-CSRF-Token header, which
// the backend compares against the session in constant time.

export async function getCsrfToken(): Promise<string> {
  const response = await fetch("/api/csrf", { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load CSRF token");
  const data = (await response.json()) as { csrf_token: string };
  return data.csrf_token;
}

export async function apiWrite(
  path: string,
  method: "POST" | "PUT" | "DELETE",
  token: string,
  body?: unknown,
): Promise<Response> {
  return fetch(path, {
    method,
    headers: {
      "X-CSRF-Token": token,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}
