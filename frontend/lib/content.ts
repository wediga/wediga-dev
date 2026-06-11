import { cookies } from "next/headers";
import { backendUrl } from "./backend";
import type {
  About,
  Contact,
  CuratedRepo,
  Impressum,
  Project,
  SkillCategory,
} from "./types";

// Server-side reads for the public and recruiter views. Server Components call
// these, so the Next.js server talks to the backend and the browser only ever
// sees the frontend origin. Reads are uncached so an admin edit shows at once.
async function getJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(backendUrl(path), { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

// Gated reads forward the visitor's session cookie, so the backend can apply
// the recruiter-or-admin gate. The page itself is guarded by the recruiter
// layout, this only carries the session through to the data fetch.
async function getJsonWithSession<T>(path: string): Promise<T | null> {
  try {
    const cookieHeader = (await cookies()).toString();
    const response = await fetch(backendUrl(path), {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function getAbout(): Promise<About | null> {
  return getJson<About>("/content/about");
}

export function getContact(): Promise<Contact | null> {
  return getJsonWithSession<Contact>("/content/contact");
}

export function getImpressum(): Promise<Impressum | null> {
  return getJson<Impressum>("/content/impressum");
}

export async function getProjects(): Promise<Project[]> {
  return (await getJsonWithSession<Project[]>("/content/projects")) ?? [];
}

export async function getSkills(): Promise<SkillCategory[]> {
  return (await getJson<SkillCategory[]>("/content/skills")) ?? [];
}

// The curated GitHub repos, gated like the portfolio. The backend already
// filters to visible repos, orders pinned first and resolves the effective
// description, so the view only renders what it receives.
export async function getCuratedRepos(): Promise<CuratedRepo[]> {
  return (await getJsonWithSession<CuratedRepo[]>("/github/repos")) ?? [];
}
