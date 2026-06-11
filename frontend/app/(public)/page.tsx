import Link from "next/link";
import { Markdown } from "@/components/Markdown";
import { getAbout, getSkills } from "@/lib/content";

export default async function LandingPage() {
  const [about, skills] = await Promise.all([getAbout(), getSkills()]);

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-3xl font-bold">wediga.dev</h1>

      <section className="mt-6">
        {about && about.text ? (
          <Markdown>{about.text}</Markdown>
        ) : (
          <p className="text-gray-500">No about text yet.</p>
        )}
      </section>

      {skills.length > 0 ? (
        <section className="mt-10">
          <h2 className="text-xl font-semibold">Skills</h2>
          <div className="mt-4 space-y-4">
            {skills.map((category) => (
              <div key={category.id}>
                <h3 className="font-medium">{category.name}</h3>
                <ul className="mt-1 flex flex-wrap gap-2">
                  {category.skills.map((skill) => (
                    <li
                      key={skill.id}
                      className="rounded bg-gray-100 px-2 py-1 text-sm"
                    >
                      {skill.name}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <footer className="mt-12 flex gap-4 text-sm text-gray-500">
        <Link href="/impressum" className="hover:underline">
          Impressum
        </Link>
        <Link href="/login" className="hover:underline">
          Login
        </Link>
      </footer>
    </main>
  );
}
