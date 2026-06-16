import { Markdown } from "@/components/Markdown";
import type { About, SkillCategory } from "@/lib/types";

// The real, readable landing content (about + skills) sourced from the BFF. It is
// always present in the DOM for screen readers, search engines and the E2E suite.
// The Hero decides where to mount it: a visible stacked column under reduced
// motion, or an accessible layer behind the canvas during the full-motion ride.
// Mapping this content onto the section planets is Phase H2.
export function LandingContent({
  about,
  skills,
}: {
  about: About | null;
  skills: SkillCategory[];
}) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-bold text-white">wediga.dev</h1>

      <section className="mt-6 text-zinc-100">
        {about && about.text ? (
          <Markdown>{about.text}</Markdown>
        ) : (
          <p className="text-zinc-400">No about text yet.</p>
        )}
      </section>

      {skills.length > 0 ? (
        <section className="mt-10">
          <h2 className="text-xl font-semibold text-white">Skills</h2>
          <div className="mt-4 space-y-4">
            {skills.map((category) => (
              <div key={category.id}>
                <h3 className="font-medium text-zinc-200">{category.name}</h3>
                <ul className="mt-1 flex flex-wrap gap-2">
                  {category.skills.map((skill) => (
                    <li
                      key={skill.id}
                      className="rounded bg-white/10 px-2 py-1 text-sm text-zinc-100"
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
    </div>
  );
}
