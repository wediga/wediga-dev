"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { SkillCategory } from "@/lib/types";
import {
  ADMIN_INPUT,
  AdminButton,
  ConfirmButton,
  EmptyState,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

export default function AdminSkillsPage() {
  const token = useCsrf();
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [newCategory, setNewCategory] = useState("");
  const [newSkill, setNewSkill] = useState<Record<number, string>>({});
  const { run, get, set } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/content/skills", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: SkillCategory[]) => setCategories(data))
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

  function setCategoryName(id: number, name: string) {
    setCategories((current) =>
      current.map((category) =>
        category.id === id ? { ...category, name } : category,
      ),
    );
  }

  function setSkillName(categoryId: number, skillId: number, name: string) {
    setCategories((current) =>
      current.map((category) =>
        category.id === categoryId
          ? {
              ...category,
              skills: category.skills.map((skill) =>
                skill.id === skillId ? { ...skill, name } : skill,
              ),
            }
          : category,
      ),
    );
  }

  // Keyed so each control reports its own outcome. On success the list reloads
  // so the inputs reflect the committed state.
  function write(
    key: string,
    path: string,
    method: "POST" | "PUT" | "DELETE",
    messages: { success: string; error: string },
    body?: unknown,
  ) {
    return run(
      key,
      async () => {
        const response = await apiWrite(path, method, token, body);
        if (response.ok) await load();
        return response.ok;
      },
      messages,
    );
  }

  async function addCategory() {
    if (!newCategory.trim()) return;
    const ok = await write(
      "add-category",
      "/api/content/skills/categories",
      "POST",
      { success: "Added", error: "Couldn't add. Try again." },
      { name: newCategory },
    );
    if (ok) setNewCategory("");
  }

  async function addSkill(categoryId: number) {
    const name = (newSkill[categoryId] ?? "").trim();
    if (!name) return;
    const ok = await write(
      `cat-${categoryId}-add`,
      `/api/content/skills/categories/${categoryId}/skills`,
      "POST",
      { success: "Added", error: "Couldn't add. Try again." },
      { name },
    );
    if (ok) setNewSkill((current) => ({ ...current, [categoryId]: "" }));
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Skills</h1>
      <p className="mt-1 text-sm text-muted">
        Categories and the skills inside them, shown on the landing page.
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
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={category.name}
                onChange={(event) =>
                  setCategoryName(category.id, event.target.value)
                }
                aria-label="Category name"
                className="min-w-[12rem] flex-1 border-0 border-b border-line bg-transparent px-0 pb-1.5 text-lg font-semibold text-ink transition-colors hover:border-muted-2 focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60"
              />
              <AdminButton
                pending={get(`cat-${category.id}-rename`).state === "pending"}
                pendingLabel="Saving…"
                onClick={() =>
                  write(
                    `cat-${category.id}-rename`,
                    `/api/content/skills/categories/${category.id}`,
                    "PUT",
                    { success: "Saved", error: "Couldn't save." },
                    { name: category.name, sort_order: category.sort_order },
                  )
                }
              >
                Rename
              </AdminButton>
              <ConfirmButton
                label="Delete"
                prompt="Delete this category?"
                pendingLabel="Deleting…"
                pending={get(`cat-${category.id}-delete`).state === "pending"}
                onConfirm={() =>
                  write(
                    `cat-${category.id}-delete`,
                    `/api/content/skills/categories/${category.id}`,
                    "DELETE",
                    { success: "Deleted", error: "Couldn't delete." },
                  )
                }
              />
              <Feedback status={get(`cat-${category.id}-rename`)} />
              <Feedback status={get(`cat-${category.id}-delete`)} />
            </div>

            <p className="mt-5 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted-2">
              Skills
            </p>
            <ul className="mt-2 divide-y divide-line border-t border-line">
              {category.skills.map((skill) => (
                <li
                  key={skill.id}
                  className="flex flex-wrap items-center gap-2 py-2.5"
                >
                  <input
                    value={skill.name}
                    onChange={(event) =>
                      setSkillName(category.id, skill.id, event.target.value)
                    }
                    aria-label="Skill name"
                    className={`${ADMIN_INPUT} flex-1`}
                  />
                  <AdminButton
                    pending={get(`skill-${skill.id}-rename`).state === "pending"}
                    pendingLabel="Saving…"
                    onClick={() =>
                      write(
                        `skill-${skill.id}-rename`,
                        `/api/content/skills/${skill.id}`,
                        "PUT",
                        { success: "Saved", error: "Couldn't save." },
                        { name: skill.name, sort_order: skill.sort_order },
                      )
                    }
                  >
                    Rename
                  </AdminButton>
                  <ConfirmButton
                    label="Delete"
                    prompt="Delete this skill?"
                    pendingLabel="Deleting…"
                    pending={get(`skill-${skill.id}-delete`).state === "pending"}
                    onConfirm={() =>
                      write(
                        `skill-${skill.id}-delete`,
                        `/api/content/skills/${skill.id}`,
                        "DELETE",
                        { success: "Deleted", error: "Couldn't delete." },
                      )
                    }
                  />
                  <Feedback status={get(`skill-${skill.id}-rename`)} />
                  <Feedback status={get(`skill-${skill.id}-delete`)} />
                </li>
              ))}
            </ul>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <input
                value={newSkill[category.id] ?? ""}
                onChange={(event) =>
                  setNewSkill((current) => ({
                    ...current,
                    [category.id]: event.target.value,
                  }))
                }
                placeholder="New skill"
                aria-label="New skill name"
                className={`${ADMIN_INPUT} flex-1`}
              />
              <AdminButton
                variant="primary"
                pending={get(`cat-${category.id}-add`).state === "pending"}
                pendingLabel="Adding…"
                onClick={() => addSkill(category.id)}
              >
                Add skill
              </AdminButton>
              <Feedback status={get(`cat-${category.id}-add`)} />
            </div>
          </div>
        ))}
        {categories.length === 0 ? (
          <EmptyState>No categories yet. Add the first one below.</EmptyState>
        ) : null}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <input
          value={newCategory}
          onChange={(event) => setNewCategory(event.target.value)}
          placeholder="New category"
          aria-label="New category name"
          className={`${ADMIN_INPUT} flex-1`}
        />
        <AdminButton
          variant="primary"
          pending={get("add-category").state === "pending"}
          pendingLabel="Adding…"
          onClick={addCategory}
        >
          Add category
        </AdminButton>
        <Feedback status={get("add-category")} />
      </div>
    </div>
  );
}
