// Shared content types, mirroring the backend pydantic schemas.

export interface About {
  text: string;
}

export interface Contact {
  name: string;
  email: string;
  github: string | null;
  linkedin: string | null;
}

export interface ImpressumAddress {
  street: string;
  city: string;
}

export interface Impressum {
  name: string;
  email: string;
  github: string | null;
  linkedin: string | null;
  address: ImpressumAddress | null;
}

export interface Project {
  id: number;
  name: string;
  tagline: string | null;
  problem: string | null;
  solution: string | null;
  learning: string | null;
  tech_stack: string[];
  demo_link: string | null;
  github_link: string | null;
  status: string | null;
  sort_order: number;
  visible: boolean;
}

export interface RecruiterLink {
  id: number;
  label: string | null;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  view_count: number;
  last_viewed_at: string | null;
  active: boolean;
}

// The create response carries the plaintext token once; it is never returned
// again by any later read.
export interface RecruiterLinkCreated extends RecruiterLink {
  token: string;
}

// The full repo row for the admin: mirrored GitHub fields plus curation. The
// mirrored fields are read-only in the UI; only the curation fields are sent
// back on a write.
export interface GithubRepo {
  id: number;
  name: string;
  description: string | null;
  language: string | null;
  stars: number | null;
  url: string | null;
  last_push: string | null;
  last_sync: string | null;
  visible: boolean;
  pinned: boolean;
  description_override: string | null;
  sort_order: number;
}

// The curated repo as the recruiter view receives it. ``description`` is
// already the effective text (override when set, otherwise the GitHub one).
export interface CuratedRepo {
  name: string;
  description: string | null;
  language: string | null;
  stars: number | null;
  url: string | null;
  last_push: string | null;
  pinned: boolean;
}

export interface Skill {
  id: number;
  name: string;
  sort_order: number;
}

export interface SkillCategory {
  id: number;
  name: string;
  sort_order: number;
  skills: Skill[];
}
