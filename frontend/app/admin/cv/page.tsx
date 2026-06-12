"use client";

import { useCallback, useEffect, useState } from "react";
import { getCsrfToken } from "@/lib/adminClient";

// The CV is a single uploaded PDF. This page shows whether one is present and
// lets the admin upload or replace it. The upload posts the file through the
// BFF, which forwards the multipart body, the session cookie and the CSRF token
// to the admin-gated backend endpoint.
export default function AdminCvPage() {
  const [present, setPresent] = useState<boolean | null>(null);
  const [status, setStatus] = useState("");

  const loadStatus = useCallback(() => {
    return fetch("/api/cv/status", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setPresent(data ? Boolean(data.present) : false))
      .catch(() => setStatus("Load failed"));
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  async function upload(file: File) {
    setStatus("Uploading...");
    const csrf = await getCsrfToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/cv", {
      method: "POST",
      headers: { "X-CSRF-Token": csrf },
      body: form,
    });
    if (response.ok) {
      await loadStatus();
      setStatus("CV uploaded");
    } else if (response.status === 415 || response.status === 422) {
      setStatus("Upload failed: only a PDF file is accepted");
    } else if (response.status === 413) {
      setStatus("Upload failed: the file is too large");
    } else {
      setStatus("Upload failed");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">CV</h1>
      <p className="mt-1 text-sm text-gray-500">
        Upload the CV as a PDF. It replaces the current file and is served to the
        protected CV page as a download.
      </p>
      {status ? <p className="mt-2 text-sm text-gray-600">{status}</p> : null}

      <section className="mt-6 rounded border border-gray-200 p-4">
        <p className="text-sm text-gray-700">
          {present === null
            ? "Checking..."
            : present
              ? "A CV PDF is currently uploaded."
              : "No CV uploaded yet."}
        </p>
        <input
          type="file"
          accept="application/pdf"
          className="mt-3 text-sm"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) upload(file);
            event.target.value = "";
          }}
        />
        {present ? (
          <p className="mt-3 text-sm">
            <a
              href="/api/cv/download"
              target="_blank"
              rel="noreferrer"
              className="text-gray-900 underline"
            >
              View current PDF
            </a>
          </p>
        ) : null}
      </section>
    </div>
  );
}
