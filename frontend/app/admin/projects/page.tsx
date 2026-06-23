"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { Project } from "@/lib/types";
import {
  AdminButton,
  AdminField,
  ConfirmButton,
  EmptyState,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

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

const SHORT_FIELDS: { key: keyof FormState; label: string }[] = [
  { key: "tagline", label: "Tagline" },
  { key: "status", label: "Status" },
  { key: "demo_link", label: "Demo link" },
  { key: "github_link", label: "GitHub link" },
];
const AREA_FIELDS: { key: keyof FormState; label: string }[] = [
  { key: "problem", label: "Problem" },
  { key: "solution", label: "Solution" },
  { key: "learning", label: "Learning" },
];

export default function AdminProjectsPage() {
  const token = useCsrf();
  const [projects, setProjects] = useState<Project[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const { run, get, set } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/content/projects", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: Project[]) => setProjects(data))
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't load the projects. Reload the page.",
        }),
      );
  }, [set]);

  useEffect(() => {
    load();
  }, [load]);

  function startNew() {
    setEditingId(null);
    setForm(EMPTY);
  }

  function startEdit(project: Project) {
    setEditingId(project.id);
    setForm(toForm(project));
  }

  function update<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const save = () =>
    run(
      "save",
      async () => {
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
          startNew();
          await load();
        }
        return response.ok;
      },
      { success: "Saved", error: "Couldn't save. Try again." },
    );

  const remove = (id: number) =>
    run(
      `delete-${id}`,
      async () => {
        const response = await apiWrite(
          `/api/content/projects/${id}`,
          "DELETE",
          token,
        );
        if (response.ok) {
          if (editingId === id) startNew();
          await load();
        }
        return response.ok;
      },
      { success: "Deleted", error: "Couldn't delete. Try again." },
    );

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Projects</h1>
      <p className="mt-1 text-sm text-muted">
        Showcase projects, ordered by sort order.
      </p>
      {get("load").state === "error" ? (
        <div className="mt-4">
          <Feedback status={get("load")} />
        </div>
      ) : null}

      {projects.length === 0 ? (
        <div className="mt-6">
          <EmptyState>No projects yet. Create the first one below.</EmptyState>
        </div>
      ) : (
        <ul className="mt-6 divide-y divide-line overflow-hidden rounded-lg border border-line">
          {projects.map((project) => (
            <li
              key={project.id}
              className="flex flex-wrap items-center justify-between gap-3 bg-surface/40 px-4 py-3"
            >
              <span className="text-sm text-ink">
                {project.name}
                {project.visible ? null : (
                  <span className="ml-2 text-xs text-muted">(hidden)</span>
                )}
              </span>
              <span className="flex flex-wrap items-center gap-2">
                <AdminButton onClick={() => startEdit(project)}>Edit</AdminButton>
                <ConfirmButton
                  label="Delete"
                  prompt="Delete this project?"
                  pendingLabel="Deleting…"
                  pending={get(`delete-${project.id}`).state === "pending"}
                  onConfirm={() => remove(project.id)}
                />
                <Feedback status={get(`delete-${project.id}`)} />
              </span>
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-9 text-base font-semibold text-ink">
        {editingId === null ? "New project" : "Edit project"}
      </h2>
      <div className="mt-4 space-y-4">
        <AdminField
          label="Name"
          value={form.name}
          onChange={(value) => update("name", value)}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {SHORT_FIELDS.map((field) => (
            <AdminField
              key={field.key}
              label={field.label}
              value={form[field.key] as string}
              onChange={(value) => update(field.key, value as never)}
            />
          ))}
        </div>
        <AdminField
          label="Tech stack"
          hint="Comma separated"
          value={form.tech_stack}
          onChange={(value) => update("tech_stack", value)}
        />
        {AREA_FIELDS.map((field) => (
          <AdminField
            key={field.key}
            label={field.label}
            multiline
            rows={3}
            value={form[field.key] as string}
            onChange={(value) => update(field.key, value as never)}
          />
        ))}
        <div className="grid gap-4 sm:grid-cols-2">
          <AdminField
            label="Sort order"
            type="number"
            value={String(form.sort_order)}
            onChange={(value) => update("sort_order", Number(value) || 0)}
          />
          <label className="flex items-center gap-2.5 self-end pb-2.5">
            <input
              type="checkbox"
              checked={form.visible}
              onChange={(event) => update("visible", event.target.checked)}
              className="size-4 accent-[var(--accent)]"
            />
            <span className="text-sm text-muted">Visible on the site</span>
          </label>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <AdminButton
          variant="primary"
          pending={get("save").state === "pending"}
          pendingLabel="Saving…"
          onClick={save}
        >
          {editingId === null ? "Create" : "Save"}
        </AdminButton>
        {editingId !== null ? (
          <AdminButton onClick={startNew}>Cancel</AdminButton>
        ) : null}
        <Feedback status={get("save")} />
      </div>
    </div>
  );
}
