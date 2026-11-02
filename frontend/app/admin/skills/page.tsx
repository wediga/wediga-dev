"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { SkillCategory, Technology } from "@/lib/types";
import {
  ADMIN_INPUT,
  AdminButton,
  ConfirmButton,
  EmptyState,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

const SKILLS = "/api/content/skills";
const CATEGORIES = `${SKILLS}/categories`;
const TECHNOLOGIES = "/api/content/technologies";

// The value of the "No category" option in the category select.
const NO_CATEGORY = "";

const TOPIC_HINT = "lowercase letters, digits and hyphens, not taken yet";

// Sends a write and reloads the page data when it went through.
type Write = (
  path: string,
  method: "POST" | "PUT" | "DELETE",
  body?: unknown,
) => Promise<boolean>;

type Draft = Pick<Technology, "name" | "topic" | "skill_category_id">;

// "Technology" on an existing row, "New technology" in the form to add one.
function TechnologyFields({
  label,
  draft,
  onChange,
}: {
  label: string;
  draft: Draft;
  onChange: (draft: Draft) => void;
}) {
  return (
    <>
      <input
        value={draft.name}
        onChange={(event) => onChange({ ...draft, name: event.target.value })}
        placeholder="Name"
        aria-label={`${label} name`}
        className={`${ADMIN_INPUT} min-w-0 flex-1`}
      />
      <input
        value={draft.topic}
        onChange={(event) => onChange({ ...draft, topic: event.target.value })}
        placeholder="GitHub topic"
        aria-label={`${label} topic`}
        className={`${ADMIN_INPUT} w-36 font-mono`}
      />
    </>
  );
}

function TechnologyRow({
  technology,
  categories,
  write,
}: {
  technology: Technology;
  categories: SkillCategory[];
  write: Write;
}) {
  const [draft, setDraft] = useState<Draft>({
    name: technology.name,
    topic: technology.topic,
    skill_category_id: technology.skill_category_id,
  });
  const { run, get } = useActionFeedback();
  const path = `${TECHNOLOGIES}/${technology.id}`;

  return (
    <li className="flex flex-wrap items-center gap-2 py-2.5">
      <TechnologyFields label="Technology" draft={draft} onChange={setDraft} />
      <select
        value={draft.skill_category_id ?? NO_CATEGORY}
        onChange={(event) =>
          setDraft({ ...draft, skill_category_id: event.target.value || null })
        }
        aria-label="Category"
        className={`${ADMIN_INPUT} w-36`}
      >
        <option value={NO_CATEGORY}>No category</option>
        {categories.map((category) => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </select>
      <AdminButton
        pending={get("save").state === "pending"}
        pendingLabel="Saving…"
        onClick={() =>
          run("save", () => write(path, "PUT", draft), {
            success: "Saved",
            error: `Couldn't save. Topic: ${TOPIC_HINT}.`,
          })
        }
      >
        Save
      </AdminButton>
      <ConfirmButton
        label="Delete"
        prompt="Delete this technology?"
        pendingLabel="Deleting…"
        pending={get("delete").state === "pending"}
        onConfirm={() =>
          run("delete", () => write(path, "DELETE"), {
            success: "Deleted",
            error: "Couldn't delete.",
          })
        }
      />
      <Feedback status={get("save")} />
      <Feedback status={get("delete")} />
    </li>
  );
}

function AddTechnology({
  categoryId,
  write,
}: {
  categoryId: string | null;
  write: Write;
}) {
  const empty: Draft = { name: "", topic: "", skill_category_id: categoryId };
  const [draft, setDraft] = useState<Draft>(empty);
  const { run, get } = useActionFeedback();

  async function add() {
    if (!draft.name.trim() || !draft.topic.trim()) return;

    const ok = await run("add", () => write(TECHNOLOGIES, "POST", draft), {
      success: "Added",
      error: `Couldn't add. Topic: ${TOPIC_HINT}.`,
    });

    if (ok) setDraft(empty);
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <TechnologyFields
        label="New technology"
        draft={draft}
        onChange={setDraft}
      />
      <AdminButton
        variant="primary"
        pending={get("add").state === "pending"}
        pendingLabel="Adding…"
        onClick={add}
      >
        Add technology
      </AdminButton>
      <Feedback status={get("add")} />
    </div>
  );
}

function TechnologyList({
  technologies,
  categories,
  categoryId,
  write,
}: {
  technologies: Technology[];
  categories: SkillCategory[];
  categoryId: string | null;
  write: Write;
}) {
  return (
    <>
      <ul className="mt-2 divide-y divide-line border-t border-line">
        {technologies
          .filter((technology) => technology.skill_category_id === categoryId)
          .map((technology) => (
            <TechnologyRow
              key={technology.id}
              technology={technology}
              categories={categories}
              write={write}
            />
          ))}
      </ul>
      <AddTechnology categoryId={categoryId} write={write} />
    </>
  );
}

function CategoryHeader({
  category,
  write,
}: {
  category: SkillCategory;
  write: Write;
}) {
  const [name, setName] = useState(category.name);
  const { run, get } = useActionFeedback();
  const path = `${CATEGORIES}/${category.id}`;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        value={name}
        onChange={(event) => setName(event.target.value)}
        aria-label="Category name"
        className="min-w-[12rem] flex-1 border-0 border-b border-line bg-transparent px-0 pb-1.5 text-lg font-semibold text-ink transition-colors hover:border-muted-2 focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
      />
      <AdminButton
        pending={get("rename").state === "pending"}
        pendingLabel="Saving…"
        onClick={() =>
          run(
            "rename",
            () => write(path, "PUT", { name, sort_order: category.sort_order }),
            { success: "Saved", error: "Couldn't save." },
          )
        }
      >
        Rename
      </AdminButton>
      <ConfirmButton
        label="Delete"
        prompt="Delete this category? Its technologies stay, without a category."
        pendingLabel="Deleting…"
        pending={get("delete").state === "pending"}
        onConfirm={() =>
          run("delete", () => write(path, "DELETE"), {
            success: "Deleted",
            error: "Couldn't delete.",
          })
        }
      />
      <Feedback status={get("rename")} />
      <Feedback status={get("delete")} />
    </div>
  );
}

function AddCategory({ write }: { write: Write }) {
  const [name, setName] = useState("");
  const { run, get } = useActionFeedback();

  async function add() {
    if (!name.trim()) return;

    const ok = await run("add", () => write(CATEGORIES, "POST", { name }), {
      success: "Added",
      error: "Couldn't add. Try again.",
    });

    if (ok) setName("");
  }

  return (
    <div className="mt-6 flex flex-wrap items-center gap-2">
      <input
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="New category"
        aria-label="New category name"
        className={`${ADMIN_INPUT} flex-1`}
      />
      <AdminButton
        variant="primary"
        pending={get("add").state === "pending"}
        pendingLabel="Adding…"
        onClick={add}
      >
        Add category
      </AdminButton>
      <Feedback status={get("add")} />
    </div>
  );
}

const SECTION_LABEL =
  "mt-5 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted-2";

export default function AdminSkillsPage() {
  const token = useCsrf();
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [technologies, setTechnologies] = useState<Technology[]>([]);
  const { get, set } = useActionFeedback();

  const load = useCallback(() => {
    return Promise.all(
      [SKILLS, TECHNOLOGIES].map((path) =>
        fetch(path, { cache: "no-store" }).then((response) => {
          if (!response.ok) throw new Error(`${path}: ${response.status}`);

          return response.json();
        }),
      ),
    )
      .then(([skills, technologies]) => {
        setCategories(skills);
        setTechnologies(technologies);
      })
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't load the skills. Reload the page.",
        }),
      );
  }, [set]);

  useEffect(() => {
    load();
  }, [load]);

  const write: Write = useCallback(
    async (path, method, body) => {
      const response = await apiWrite(path, method, token, body);

      if (response.ok) await load();

      return response.ok;
    },
    [token, load],
  );

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Skills</h1>
      <p className="mt-1 text-sm text-muted">
        Technologies by their GitHub topic. In a category they show as skills on
        the landing page.
      </p>
      {get("load").state === "error" ? (
        <div className="mt-4">
          <Feedback status={get("load")} />
        </div>
      ) : null}

      <div className="mt-6 space-y-5">
        {categories.map((category) => (
          <div
            key={category.id}
            className="rounded-lg border border-line bg-surface/40 p-4 sm:p-5"
          >
            <CategoryHeader category={category} write={write} />
            <p className={SECTION_LABEL}>Technologies</p>
            <TechnologyList
              technologies={technologies}
              categories={categories}
              categoryId={category.id}
              write={write}
            />
          </div>
        ))}
        {categories.length === 0 ? (
          <EmptyState>No categories yet. Add the first one below.</EmptyState>
        ) : null}
      </div>

      <AddCategory write={write} />

      <div className="mt-8">
        <h2 className="text-lg font-semibold text-ink">
          Technologies without category
        </h2>
        <p className="mt-1 text-sm text-muted">
          Not shown as skills. Pick a category to show one.
        </p>
        <TechnologyList
          technologies={technologies}
          categories={categories}
          categoryId={null}
          write={write}
        />
      </div>
    </div>
  );
}
