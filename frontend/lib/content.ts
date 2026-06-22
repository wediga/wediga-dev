import { headers } from "next/headers";
import { backendUrl } from "./backend";
import type {
  Contact,
  CvStatus,
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
// layout, this only carries the session through to the data fetch. The raw
// cookie header is forwarded verbatim, the same way the BFF route handlers do
// it, because re-serializing the cookies (cookies().toString()) re-encodes the
// signed session value and the backend then rejects it.
async function getJsonWithSession<T>(path: string): Promise<T | null> {
  try {
    const cookieHeader = (await headers()).get("cookie");
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

// Whether the visitor carries a valid recruiter (or admin) session, asked of the
// backend the same way the recruiter layout gates its pages. Read-only: the
// landing uses it to flip the access door between login and portfolio, it does
// not gate any content. The raw cookie header is forwarded verbatim, like the
// gated reads, so the signed session value is not re-encoded.
export async function getRecruiterSession(): Promise<boolean> {
  try {
    const cookieHeader = (await headers()).get("cookie");
    const response = await fetch(backendUrl("/recruiter/session"), {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
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

// Whether a CV PDF is currently uploaded, gated like the portfolio. The page
// uses this to decide whether to show the download and preview.
export async function getCvStatus(): Promise<CvStatus> {
  return (await getJsonWithSession<CvStatus>("/cv/status")) ?? { present: false };
}
