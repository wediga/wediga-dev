// Server-side base URL of the FastAPI backend, used only by Server Components
// and BFF route handlers, never the browser. Resolves to the internal service
// name "backend" in production and localhost in local development.
export function backendUrl(path: string): string {
  const base = process.env.BACKEND_URL ?? "http://localhost:8000";
  return `${base}${path}`;
}
