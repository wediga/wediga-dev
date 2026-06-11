"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { SkillCategory } from "@/lib/types";

export default function AdminSkillsPage() {
  const token = useCsrf();
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [newCategory, setNewCategory] = useState("");
  const [newSkill, setNewSkill] = useState<Record<number, string>>({});
  const [status, setStatus] = useState("");

  const load = useCallback(() => {
    return fetch("/api/content/skills", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: SkillCategory[]) => setCategories(data));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Edit category and skill names in place, then send the current value.
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

  async function send(
    path: string,
    method: "POST" | "PUT" | "DELETE",
    body?: unknown,
  ): Promise<boolean> {
    const response = await apiWrite(path, method, token, body);
    if (response.ok) {
      await load();
      return true;
    }
    setStatus("Request failed");
    return false;
  }

  async function addCategory() {
    if (!newCategory.trim()) return;
    const ok = await send("/api/content/skills/categories", "POST", {
      name: newCategory,
    });
    if (ok) setNewCategory("");
  }

  async function addSkill(categoryId: number) {
    const name = (newSkill[categoryId] ?? "").trim();
    if (!name) return;
    const ok = await send(
      `/api/content/skills/categories/${categoryId}/skills`,
      "POST",
      { name },
    );
    if (ok) setNewSkill((current) => ({ ...current, [categoryId]: "" }));
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Skills</h1>
      {status ? <p className="mt-2 text-sm text-gray-600">{status}</p> : null}

      <div className="mt-6 space-y-6">
        {categories.map((category) => (
          <div key={category.id} className="rounded border border-gray-200 p-4">
            <div className="flex items-center gap-2">
              <input
                value={category.name}
                onChange={(event) =>
                  setCategoryName(category.id, event.target.value)
                }
                className="flex-1 rounded border border-gray-300 px-3 py-1 font-semibold"
              />
              <button
                onClick={() =>
                  send(
                    `/api/content/skills/categories/${category.id}`,
                    "PUT",
                    { name: category.name, sort_order: category.sort_order },
                  )
                }
                className="rounded border border-gray-300 px-3 py-1 text-sm"
              >
                Rename
              </button>
              <button
                onClick={() =>
                  send(`/api/content/skills/categories/${category.id}`, "DELETE")
                }
                className="rounded border border-gray-300 px-3 py-1 text-sm"
              >
                Delete
              </button>
            </div>

            <ul className="mt-3 space-y-2">
              {category.skills.map((skill) => (
                <li key={skill.id} className="flex items-center gap-2">
                  <input
                    value={skill.name}
                    onChange={(event) =>
                      setSkillName(category.id, skill.id, event.target.value)
                    }
                    className="flex-1 rounded border border-gray-300 px-3 py-1 text-sm"
                  />
                  <button
                    onClick={() =>
                      send(`/api/content/skills/${skill.id}`, "PUT", {
                        name: skill.name,
                        sort_order: skill.sort_order,
                      })
                    }
                    className="rounded border border-gray-300 px-3 py-1 text-sm"
                  >
                    Rename
                  </button>
                  <button
                    onClick={() =>
                      send(`/api/content/skills/${skill.id}`, "DELETE")
                    }
                    className="rounded border border-gray-300 px-3 py-1 text-sm"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>

            <div className="mt-3 flex items-center gap-2">
              <input
                value={newSkill[category.id] ?? ""}
                onChange={(event) =>
                  setNewSkill((current) => ({
                    ...current,
                    [category.id]: event.target.value,
                  }))
                }
                placeholder="New skill"
                className="flex-1 rounded border border-gray-300 px-3 py-1 text-sm"
              />
              <button
                onClick={() => addSkill(category.id)}
                className="rounded bg-gray-900 px-3 py-1 text-sm text-white"
              >
                Add skill
              </button>
            </div>
          </div>
        ))}
        {categories.length === 0 ? (
          <p className="text-sm text-gray-500">No categories yet.</p>
        ) : null}
      </div>

      <div className="mt-6 flex items-center gap-2">
        <input
          value={newCategory}
          onChange={(event) => setNewCategory(event.target.value)}
          placeholder="New category"
          className="flex-1 rounded border border-gray-300 px-3 py-2"
        />
        <button
          onClick={addCategory}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white"
        >
          Add category
        </button>
      </div>
    </div>
  );
}
