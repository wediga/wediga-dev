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
