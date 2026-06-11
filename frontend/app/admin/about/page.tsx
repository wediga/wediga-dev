"use client";

import { useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";

export default function AdminAboutPage() {
  const token = useCsrf();
  const [text, setText] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("/api/content/about", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : { text: "" }))
      .then((data) => setText(data.text ?? ""))
      .catch(() => setStatus("Load failed"));
  }, []);

  async function save() {
    const response = await apiWrite("/api/content/about", "PUT", token, { text });
    setStatus(response.ok ? "Saved" : "Save failed");
  }

  async function remove() {
    const response = await apiWrite("/api/content/about", "DELETE", token);
    if (response.ok) {
      setText("");
      setStatus("Deleted");
    } else {
      setStatus("Delete failed");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">About</h1>
      <p className="mt-1 text-sm text-gray-500">Markdown is rendered on the site.</p>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={16}
        className="mt-4 w-full rounded border border-gray-300 p-3 font-mono text-sm"
      />
      <div className="mt-3 flex items-center gap-3">
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
