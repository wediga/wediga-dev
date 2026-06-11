// Server-side base URL of the FastAPI backend. The browser never uses this;
// only Server Components and BFF route handlers call the backend, over the
// internal network in production (service name "backend") and over localhost
// in local development.
export function backendUrl(path: string): string {
  const base = process.env.BACKEND_URL ?? "http://localhost:8000";
  return `${base}${path}`;
}
