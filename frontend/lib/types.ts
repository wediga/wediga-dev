// Shared content types, mirroring the backend pydantic schemas.

import type { StatusKey } from "./projectStatus";

// The kinds of link a profile can carry with their labels, the same kinds as
// ``LinkKind`` in the backend schemas (a backend test compares both).
export const LINK_LABELS = {
  github: "GitHub",
  linkedin: "LinkedIn",
  website: "Website",
} as const;

export type LinkKind = keyof typeof LINK_LABELS;

export type ProfileLinks = Partial<Record<LinkKind, string>>;

export interface Contact {
  name: string;
  email: string;
  links: ProfileLinks;
}

// The public contact card on /hi: the contact plus the phone number, empty
// when there is none.
export interface Card extends Contact {
  phone: string;
}

export interface ProfileAddress {
  street: string;
  postal_code: string;
  city: string;
}

export interface Profile extends Contact {
  about_md: string;
  address: ProfileAddress | null;
}

// The public impressum carries only name and email.
export interface Impressum {
  name: string;
  email: string;
}

export interface RecruiterLink {
  id: string;
  label: string | null;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  view_count: number;
  last_viewed_at: string | null;
  active: boolean;
}

// The create response carries the plaintext token once, never returned again by
// any later read.
export interface RecruiterLinkCreated extends RecruiterLink {
  token: string;
}

// One run of the GitHub sync. It succeeded when it finished without an error.
export interface GithubSync {
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

// The texts of a portfolio tile, the same fields as ``TextFieldKey`` in the
// backend schemas (a backend test compares both).
export const TEXT_FIELDS = [
  "name",
  "description",
  "problem",
  "solution",
  "learning",
  "ending",
] as const;

export type TextField = (typeof TEXT_FIELDS)[number];

// A repo always has a name, every other text may be missing.
export type Texts = Partial<Record<TextField, string>> & { name: string };

export interface ProjectStatus {
  id: string;
  key: StatusKey;
  label: string;
}

// What the admin sets for a repo. A blank own text means the one from GitHub.
export interface PortfolioEntryWrite {
  project_status_id: string;
  sort_order: number;
  published: boolean;
  texts: Partial<Record<TextField, string>>;
}

export interface PortfolioEntry extends PortfolioEntryWrite {
  partly_translated: boolean;
}

// A public repo as the last successful sync saw it, with its entry if any.
export interface PortfolioRepo {
  id: string;
  texts: Texts;
  homepage_url: string | null;
  archived: boolean;
  technologies: string[];
  entry: PortfolioEntry | null;
}

export interface PortfolioAdmin {
  last_sync: GithubSync | null;
  statuses: ProjectStatus[];
  repos: PortfolioRepo[];
}

// A published repo, each text its own one or else the one from GitHub.
export interface PortfolioTile {
  id: string;
  texts: Texts;
  status: ProjectStatus;
  archived: boolean;
  technologies: string[];
  demo_url: string | null;
  github_url: string;
}

// The CV is a single uploaded PDF, its only state is whether one is present.
export interface CvStatus {
  present: boolean;
}

export interface Skill {
  id: string;
  name: string;
  sort_order: number;
}

export interface SkillCategory {
  id: string;
  name: string;
  sort_order: number;
  skills: Skill[];
}

// A technology by its GitHub topic. With a category it is a skill.
export interface Technology {
  id: string;
  topic: string;
  name: string;
  skill_category_id: string | null;
  sort_order: number | null;
}
