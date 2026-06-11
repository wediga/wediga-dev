import Link from "next/link";

const SECTIONS = [
  { href: "/admin/about", label: "About", hint: "Markdown intro text" },
  { href: "/admin/projects", label: "Projects", hint: "Showcase projects" },
  { href: "/admin/skills", label: "Skills", hint: "Categories and skills" },
  { href: "/admin/contact", label: "Contact", hint: "Contact details" },
  { href: "/admin/impressum", label: "Impressum", hint: "Legal notice" },
  { href: "/admin/links", label: "Links", hint: "Recruiter magic links" },
];

export default function AdminPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Admin</h1>
      <p className="mt-2 text-gray-600">Manage the site content.</p>
      <ul className="mt-6 grid gap-3 sm:grid-cols-2">
        {SECTIONS.map((section) => (
          <li key={section.href}>
            <Link
              href={section.href}
              className="block rounded border border-gray-200 p-4 hover:border-gray-400"
            >
              <span className="font-semibold">{section.label}</span>
              <span className="mt-1 block text-sm text-gray-500">
                {section.hint}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
