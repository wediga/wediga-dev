"use client";

import { useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import {
  AdminButton,
  AdminField,
  ConfirmButton,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

const EMPTY = { name: "", email: "", github: "", linkedin: "" };

const FIELDS: { key: keyof typeof EMPTY; label: string; type?: string }[] = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email", type: "email" },
  { key: "github", label: "GitHub" },
  { key: "linkedin", label: "LinkedIn" },
];

export default function AdminContactPage() {
  const token = useCsrf();
  const [form, setForm] = useState(EMPTY);
  const { run, get, set } = useActionFeedback();

  useEffect(() => {
    fetch("/api/content/contact", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data) {
          setForm({
            name: data.name ?? "",
            email: data.email ?? "",
            github: data.github ?? "",
            linkedin: data.linkedin ?? "",
          });
        }
      })
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't load the contact details. Reload the page.",
        }),
      );
  }, [set]);

  function update(field: keyof typeof EMPTY, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const save = () =>
    run(
      "save",
      async () => {
        const body = {
          name: form.name,
          email: form.email,
          github: form.github || null,
          linkedin: form.linkedin || null,
        };
        const response = await apiWrite(
          "/api/content/contact",
          "PUT",
          token,
          body,
        );
        return response.ok;
      },
      { success: "Saved", error: "Couldn't save. Try again." },
    );

  const remove = () =>
    run(
      "delete",
      async () => {
        const response = await apiWrite(
          "/api/content/contact",
          "DELETE",
          token,
        );
        if (response.ok) setForm(EMPTY);
        return response.ok;
      },
      { success: "Deleted", error: "Couldn't delete. Try again." },
    );

  const load = get("load");

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Contact</h1>
      <p className="mt-1 text-sm text-muted">
        Shown on the protected contact view.
      </p>
      {load.state === "error" ? (
        <p className="mt-4 text-sm text-danger">{load.message}</p>
      ) : null}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {FIELDS.map((field) => (
          <AdminField
            key={field.key}
            label={field.label}
            type={field.type}
            value={form[field.key]}
            onChange={(value) => update(field.key, value)}
          />
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <AdminButton
          variant="primary"
          pending={get("save").state === "pending"}
          pendingLabel="Saving…"
          onClick={save}
        >
          Save
        </AdminButton>
        <ConfirmButton
          label="Delete"
          prompt="Delete the contact details?"
          pendingLabel="Deleting…"
          pending={get("delete").state === "pending"}
          onConfirm={remove}
        />
        <Feedback status={get("save")} />
        <Feedback status={get("delete")} />
      </div>
    </div>
  );
}
