import { headers } from "next/headers";
import { backendUrl } from "./backend";
import { sessionCookieHeader } from "./forwarding";
import type {
  Contact,
  CvStatus,
  Impressum,
  Project,
  SkillCategory,
} from "./types";

// Server-side reads for the public and recruiter views. Called from Server
// Components, so the backend is reached only by the Next.js server and the
// browser sees just the frontend origin. Uncached, so an admin edit shows at once.
async function getJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(backendUrl(path), { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

// Gated reads forward the visitor's session cookie so the backend can apply the
// recruiter-or-admin gate. The recruiter layout already guards the page, this
// only carries the session into the data fetch. The raw cookie header is
// forwarded verbatim, like the BFF route handlers, because re-serializing it
// (cookies().toString()) re-encodes the signed session value and the backend
// then rejects it.
async function getJsonWithSession<T>(path: string): Promise<T | null> {
  try {
    const cookieHeader = (await headers()).get("cookie");
    const response = await fetch(backendUrl(path), {
      headers: sessionCookieHeader(cookieHeader),
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

// Whether the visitor carries a valid recruiter or admin session, asked of the
// backend the way the recruiter layout gates its pages. The landing uses it to
// flip the access door between login and portfolio, it gates no content itself.
// Cookie header forwarded verbatim like the gated reads, so the signed value is
// not re-encoded.
export async function getRecruiterSession(): Promise<boolean> {
  try {
    const cookieHeader = (await headers()).get("cookie");
    const response = await fetch(backendUrl("/recruiter/session"), {
      headers: sessionCookieHeader(cookieHeader),
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

// Whether a CV PDF is uploaded, gated like the portfolio. The page uses this to
// decide whether to show the download and preview.
export async function getCvStatus(): Promise<CvStatus> {
  return (await getJsonWithSession<CvStatus>("/cv/status")) ?? { present: false };
}
