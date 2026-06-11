"use client";

import { useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";

const EMPTY = {
  name: "",
  email: "",
  github: "",
  linkedin: "",
  street: "",
  city: "",
};

export default function AdminImpressumPage() {
  const token = useCsrf();
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("/api/content/impressum", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data) {
          setForm({
            name: data.name ?? "",
            email: data.email ?? "",
            github: data.github ?? "",
            linkedin: data.linkedin ?? "",
            street: data.address?.street ?? "",
            city: data.address?.city ?? "",
          });
        }
      })
      .catch(() => setStatus("Load failed"));
  }, []);

  function update(field: keyof typeof EMPTY, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    const body = {
      name: form.name,
      email: form.email,
      github: form.github || null,
      linkedin: form.linkedin || null,
      address:
        form.street || form.city
          ? { street: form.street, city: form.city }
          : null,
    };
    const response = await apiWrite("/api/content/impressum", "PUT", token, body);
    setStatus(response.ok ? "Saved" : "Save failed");
  }

  async function remove() {
    const response = await apiWrite("/api/content/impressum", "DELETE", token);
    if (response.ok) {
      setForm(EMPTY);
      setStatus("Deleted");
    } else {
      setStatus("Delete failed");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Impressum</h1>
      <div className="mt-4 space-y-3">
        {(["name", "email", "github", "linkedin", "street", "city"] as const).map(
          (field) => (
            <label key={field} className="block">
              <span className="text-sm capitalize text-gray-600">{field}</span>
              <input
                value={form[field]}
                onChange={(event) => update(field, event.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </label>
          ),
        )}
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={save}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white"
        >
          Save
        </button>
        <button
          onClick={remove}
          className="rounded border border-gray-300 px-4 py-2 text-sm"
        >
          Delete
        </button>
        {status ? <span className="text-sm text-gray-600">{status}</span> : null}
      </div>
    </div>
  );
}
