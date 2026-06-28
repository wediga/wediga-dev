import Link from "next/link";

const SECTIONS = [
  { href: "/admin/about", label: "About", hint: "Markdown intro text" },
  { href: "/admin/projects", label: "Projects", hint: "Showcase projects" },
  { href: "/admin/skills", label: "Skills", hint: "Categories and skills" },
  { href: "/admin/contact", label: "Contact", hint: "Contact details" },
  { href: "/admin/impressum", label: "Impressum", hint: "Legal notice" },
  { href: "/admin/repos", label: "Repos", hint: "GitHub sync and curation" },
  { href: "/admin/cv", label: "CV", hint: "Upload the CV PDF" },
  { href: "/admin/links", label: "Links", hint: "Recruiter magic links" },
  { href: "/admin/security", label: "Security", hint: "Two-factor login" },
];

export default function AdminPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Admin</h1>
      <p className="mt-1 text-sm text-muted">Manage the site content.</p>
      <ul className="mt-7 grid gap-3 sm:grid-cols-2">
        {SECTIONS.map((section) => (
          <li key={section.href}>
            <Link
              href={section.href}
              className="block rounded-lg border border-line bg-surface/40 p-4 transition-colors duration-150 ease-out hover:border-muted-2 hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60"
            >
              <span className="block font-medium text-ink">{section.label}</span>
              <span className="mt-1 block text-sm text-muted">
                {section.hint}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
