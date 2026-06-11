import { getCuratedRepos, getProjects } from "@/lib/content";
import { safeHref } from "@/lib/url";

export default async function PortfolioPage() {
  const [projects, repos] = await Promise.all([
    getProjects(),
    getCuratedRepos(),
  ]);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-bold">Portfolio</h1>
      <h2 className="mt-6 text-xl font-semibold">Featured projects</h2>
      {projects.length === 0 ? (
        <p className="mt-2 text-gray-500">No projects yet.</p>
      ) : (
        <div className="mt-6 space-y-8">
          {projects.map((project) => (
            <article key={project.id}>
              <header className="flex items-baseline justify-between">
                <h2 className="text-xl font-semibold">{project.name}</h2>
                {project.status ? (
                  <span className="text-sm text-gray-500">{project.status}</span>
                ) : null}
              </header>
              {project.tagline ? (
                <p className="mt-1 text-gray-700">{project.tagline}</p>
              ) : null}
              {project.problem ? (
                <p className="mt-3">
                  <span className="font-medium">Problem: </span>
                  {project.problem}
                </p>
              ) : null}
              {project.solution ? (
                <p className="mt-2">
                  <span className="font-medium">Solution: </span>
                  {project.solution}
                </p>
              ) : null}
              {project.learning ? (
                <p className="mt-2">
                  <span className="font-medium">Learned: </span>
                  {project.learning}
                </p>
              ) : null}
              {project.tech_stack.length > 0 ? (
                <ul className="mt-3 flex flex-wrap gap-2">
                  {project.tech_stack.map((tech) => (
                    <li
                      key={tech}
                      className="rounded bg-gray-100 px-2 py-1 text-sm"
                    >
                      {tech}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div className="mt-3 flex gap-4 text-sm">
                {safeHref(project.demo_link) ? (
                  <a
                    href={safeHref(project.demo_link)}
                    className="text-blue-700 underline"
                    rel="noreferrer noopener"
                  >
                    Demo
                  </a>
                ) : null}
                {safeHref(project.github_link) ? (
                  <a
                    href={safeHref(project.github_link)}
                    className="text-blue-700 underline"
                    rel="noreferrer noopener"
                  >
                    GitHub
                  </a>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}

      <h2 className="mt-12 text-xl font-semibold">GitHub repositories</h2>
      <p className="mt-1 text-sm text-gray-500">
        Public repositories, mirrored from GitHub and curated here.
      </p>
      {repos.length === 0 ? (
        <p className="mt-2 text-gray-500">No repositories yet.</p>
      ) : (
        <ul className="mt-4 space-y-4">
          {repos.map((repo) => (
            <li key={repo.name}>
              <div className="flex items-baseline justify-between gap-3">
                {safeHref(repo.url) ? (
                  <a
                    href={safeHref(repo.url)}
                    className="font-medium text-blue-700 underline"
                    rel="noreferrer noopener"
                  >
                    {repo.name}
                  </a>
                ) : (
                  <span className="font-medium">{repo.name}</span>
                )}
                <span className="shrink-0 text-sm text-gray-500">
                  {repo.language ? `${repo.language} · ` : ""}
                  {repo.stars ?? 0}★
                </span>
              </div>
              {repo.description ? (
                <p className="mt-1 text-sm text-gray-700">{repo.description}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
