import { getProjects } from "@/lib/content";
import { safeHref } from "@/lib/url";
import { STATUS_CLASS, statusKind } from "@/lib/projectStatus";
import type { Project } from "@/lib/types";

// Keep the entrance stagger short no matter how long the lists grow: late items
// should not wait seconds to appear.
const revealVar = (i: number) =>
  ({ "--reveal-i": String(Math.min(i, 6)) }) as React.CSSProperties;

export default async function PortfolioPage() {
  const projects = await getProjects();

  return (
    <div>
      <header className="reveal" style={revealVar(0)}>
        <h1 className="text-[clamp(2.2rem,4.5vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.02em] text-balance">
          Portfolio
        </h1>
        <p className="mt-4 max-w-[60ch] text-pretty leading-relaxed text-muted">
          Ausgewählte Projekte, kuratiert für den Einblick in Arbeitsweise und
          Stack.
        </p>
      </header>

      <section className="mt-16" aria-labelledby="projects-heading">
        <h2
          id="projects-heading"
          className="reveal font-mono text-xs uppercase tracking-[0.16em] text-muted-2"
          style={revealVar(1)}
        >
          Ausgewählte Projekte
        </h2>

        {projects.length === 0 ? (
          <p className="mt-6 leading-relaxed text-muted">
            Noch keine Projekte hinterlegt.
          </p>
        ) : (
          <div className="mt-2 grid gap-x-14 lg:grid-cols-2">
            {projects.map((project, i) => (
              <ProjectArticle key={project.id} project={project} index={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// One project. The name and status sit on a baseline row, the tagline carries
// the crimson accent, the three prose fields stay within a readable measure, and
// the tech stack plus links close it out. Stacked on narrow, two per row on wide.
function ProjectArticle({ project, index }: { project: Project; index: number }) {
  const kind = statusKind(project.status);
  const demo = safeHref(project.demo_link);
  const github = safeHref(project.github_link);

  return (
    <article
      className="reveal border-t border-line pt-8 pb-10"
      style={revealVar(index + 2)}
    >
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="text-[1.35rem] font-semibold leading-tight tracking-[-0.01em] text-ink">
          {project.name}
        </h3>
        {project.status ? (
          <span
            className={`shrink-0 font-mono text-xs tracking-[0.04em] ${STATUS_CLASS[kind]}`}
          >
            {project.status}
          </span>
        ) : null}
      </div>

      {project.tagline ? (
        <p className="mt-2 text-[1.02rem] leading-snug text-accent">
          {project.tagline}
        </p>
      ) : null}

      <div className="mt-5 max-w-[68ch] space-y-3 text-pretty leading-relaxed text-ink/90">
        {project.problem ? (
          <p>
            <span className="font-medium text-muted">Problem. </span>
            {project.problem}
          </p>
        ) : null}
        {project.solution ? (
          <p>
            <span className="font-medium text-muted">Lösung. </span>
            {project.solution}
          </p>
        ) : null}
        {project.learning ? (
          <p>
            <span className="font-medium text-muted">Gelernt. </span>
            {project.learning}
          </p>
        ) : null}
      </div>

      {project.tech_stack.length > 0 ? (
        <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2.5">
          {project.tech_stack.map((tech) => (
            <li
              key={tech}
              data-gen-dot
              className="gen-dot flex items-center gap-2 font-mono text-xs text-ink"
            >
              {tech}
            </li>
          ))}
        </ul>
      ) : null}

      {demo || github ? (
        <div className="mt-6 flex gap-6">
          {demo ? (
            <a href={demo} className="gen-link text-sm" rel="noreferrer noopener">
              Demo
            </a>
          ) : null}
          {github ? (
            <a
              href={github}
              className="gen-link text-sm"
              rel="noreferrer noopener"
            >
              GitHub
            </a>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
