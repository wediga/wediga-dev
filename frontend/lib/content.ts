import { backendUrl } from "./backend";
import type { About, Contact, Impressum, Project, SkillCategory } from "./types";

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

export function getAbout(): Promise<About | null> {
  return getJson<About>("/content/about");
}

export function getContact(): Promise<Contact | null> {
  return getJson<Contact>("/content/contact");
}

export function getImpressum(): Promise<Impressum | null> {
  return getJson<Impressum>("/content/impressum");
}

export async function getProjects(): Promise<Project[]> {
  return (await getJson<Project[]>("/content/projects")) ?? [];
}

export async function getSkills(): Promise<SkillCategory[]> {
  return (await getJson<SkillCategory[]>("/content/skills")) ?? [];
}
