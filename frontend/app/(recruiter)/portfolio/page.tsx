import { getProjects } from "@/lib/content";

export default async function PortfolioPage() {
  const projects = await getProjects();

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-bold">Portfolio</h1>
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
                {project.demo_link ? (
                  <a
                    href={project.demo_link}
                    className="text-blue-700 underline"
                    rel="noreferrer noopener"
                  >
                    Demo
                  </a>
                ) : null}
                {project.github_link ? (
                  <a
                    href={project.github_link}
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
    </main>
  );
}
