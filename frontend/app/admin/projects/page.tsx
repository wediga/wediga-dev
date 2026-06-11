"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { Project } from "@/lib/types";

type FormState = {
  name: string;
  tagline: string;
  problem: string;
  solution: string;
  learning: string;
  tech_stack: string;
  demo_link: string;
  github_link: string;
  status: string;
  sort_order: number;
  visible: boolean;
};

const EMPTY: FormState = {
  name: "",
  tagline: "",
  problem: "",
  solution: "",
  learning: "",
  tech_stack: "",
  demo_link: "",
  github_link: "",
  status: "",
  sort_order: 0,
  visible: true,
};

function toForm(project: Project): FormState {
  return {
    name: project.name,
    tagline: project.tagline ?? "",
    problem: project.problem ?? "",
    solution: project.solution ?? "",
    learning: project.learning ?? "",
    tech_stack: project.tech_stack.join(", "),
    demo_link: project.demo_link ?? "",
    github_link: project.github_link ?? "",
    status: project.status ?? "",
    sort_order: project.sort_order,
    visible: project.visible,
  };
}

function toBody(form: FormState) {
  return {
    name: form.name,
    tagline: form.tagline || null,
    problem: form.problem || null,
    solution: form.solution || null,
    learning: form.learning || null,
    tech_stack: form.tech_stack
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    demo_link: form.demo_link || null,
    github_link: form.github_link || null,
    status: form.status || null,
    sort_order: Number(form.sort_order) || 0,
    visible: form.visible,
  };
}

const TEXT_FIELDS: (keyof FormState)[] = [
  "name",
  "tagline",
  "demo_link",
  "github_link",
  "status",
];
const AREA_FIELDS: (keyof FormState)[] = ["problem", "solution", "learning"];

export default function AdminProjectsPage() {
  const token = useCsrf();
  const [projects, setProjects] = useState<Project[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [status, setStatus] = useState("");

  const load = useCallback(() => {
    return fetch("/api/content/projects", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: Project[]) => setProjects(data));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function startNew() {
    setEditingId(null);
    setForm(EMPTY);
    setStatus("");
  }

  function startEdit(project: Project) {
    setEditingId(project.id);
    setForm(toForm(project));
    setStatus("");
  }

  function update<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    const body = toBody(form);
    const response =
      editingId === null
        ? await apiWrite("/api/content/projects", "POST", token, body)
        : await apiWrite(
            `/api/content/projects/${editingId}`,
            "PUT",
            token,
            body,
          );
    if (response.ok) {
      setStatus("Saved");
      startNew();
      await load();
    } else {
      setStatus("Save failed");
    }
  }

  async function remove(id: number) {
    const response = await apiWrite(
      `/api/content/projects/${id}`,
      "DELETE",
      token,
    );
    if (response.ok) {
      if (editingId === id) startNew();
      await load();
    } else {
      setStatus("Delete failed");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Projects</h1>

      <ul className="mt-4 divide-y divide-gray-200 rounded border border-gray-200">
        {projects.map((project) => (
          <li
            key={project.id}
            className="flex items-center justify-between px-4 py-2"
          >
            <span>
              {project.name}
              {project.visible ? "" : " (hidden)"}
            </span>
            <span className="flex gap-2">
              <button
                onClick={() => startEdit(project)}
                className="rounded border border-gray-300 px-3 py-1 text-sm"
              >
                Edit
              </button>
              <button
                onClick={() => remove(project.id)}
                className="rounded border border-gray-300 px-3 py-1 text-sm"
              >
                Delete
              </button>
            </span>
          </li>
        ))}
        {projects.length === 0 ? (
          <li className="px-4 py-2 text-sm text-gray-500">No projects yet.</li>
        ) : null}
      </ul>

      <h2 className="mt-8 text-lg font-semibold">
        {editingId === null ? "New project" : "Edit project"}
      </h2>
      <div className="mt-3 space-y-3">
        {TEXT_FIELDS.map((field) => (
          <label key={field} className="block">
            <span className="text-sm capitalize text-gray-600">
              {field.replace("_", " ")}
            </span>
            <input
              value={form[field] as string}
              onChange={(event) => update(field, event.target.value as never)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
          </label>
        ))}
        <label className="block">
          <span className="text-sm text-gray-600">tech stack (comma separated)</span>
          <input
            value={form.tech_stack}
            onChange={(event) => update("tech_stack", event.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        {AREA_FIELDS.map((field) => (
          <label key={field} className="block">
            <span className="text-sm capitalize text-gray-600">{field}</span>
            <textarea
              value={form[field] as string}
              onChange={(event) => update(field, event.target.value as never)}
              rows={3}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
          </label>
        ))}
        <label className="block">
          <span className="text-sm text-gray-600">sort order</span>
          <input
            type="number"
            value={form.sort_order}
            onChange={(event) =>
              update("sort_order", Number(event.target.value))
            }
            className="mt-1 w-32 rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.visible}
            onChange={(event) => update("visible", event.target.checked)}
          />
          <span className="text-sm text-gray-600">visible</span>
        </label>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={save}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white"
        >
          {editingId === null ? "Create" : "Save"}
        </button>
        {editingId !== null ? (
          <button
            onClick={startNew}
            className="rounded border border-gray-300 px-4 py-2 text-sm"
          >
            Cancel
          </button>
        ) : null}
        {status ? <span className="text-sm text-gray-600">{status}</span> : null}
      </div>
    </div>
  );
}
