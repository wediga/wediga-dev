"use client";

import { useCallback, useEffect, useState } from "react";
import { getCsrfToken } from "@/lib/adminClient";
import { Feedback, useActionFeedback } from "@/components/admin/ui";

// The CV is a single uploaded PDF. This page shows whether one is present and
// lets the admin upload or replace it. The upload posts the file through the
// BFF, which forwards the multipart body, the session cookie and the CSRF token
// to the admin-gated backend endpoint.
export default function AdminCvPage() {
  const [present, setPresent] = useState<boolean | null>(null);
  const { get, set } = useActionFeedback();

  const loadStatus = useCallback(() => {
    return fetch("/api/cv/status", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setPresent(data ? Boolean(data.present) : false))
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't read the CV status. Reload the page.",
        }),
      );
  }, [set]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  async function upload(file: File) {
    set("upload", { state: "pending" });
    try {
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
        set("upload", { state: "success", message: "CV uploaded" });
      } else if (response.status === 415 || response.status === 422) {
        set("upload", {
          state: "error",
          message: "Only a PDF file is accepted.",
        });
      } else if (response.status === 413) {
        set("upload", { state: "error", message: "The file is too large." });
      } else {
        set("upload", { state: "error", message: "Upload failed. Try again." });
      }
    } catch {
      set("upload", { state: "error", message: "Upload failed. Try again." });
    }
  }

  const load = get("load");
  const uploading = get("upload").state === "pending";

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">CV</h1>
      <p className="mt-1 text-sm text-muted">
        Upload the CV as a PDF. It replaces the current file and is served to the
        protected CV page as a download.
      </p>
      {load.state === "error" ? (
        <div className="mt-4">
          <Feedback status={load} />
        </div>
      ) : null}

      <section className="mt-6 rounded-lg border border-line bg-surface/40 p-5 sm:p-6">
        <p className="text-sm text-muted">
          {present === null
            ? "Checking…"
            : present
              ? "A CV PDF is currently uploaded."
              : "No CV uploaded yet."}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept="application/pdf"
            disabled={uploading}
            className="text-sm text-muted file:mr-3 file:cursor-pointer file:rounded-sm file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-bg disabled:opacity-60"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) upload(file);
              event.target.value = "";
            }}
          />
          <Feedback status={get("upload")} pendingLabel="Uploading…" />
        </div>

        {present ? (
          <p className="mt-4 text-sm">
            <a
              href="/api/cv/download"
              target="_blank"
              rel="noreferrer"
              className="text-accent underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60"
            >
              View current PDF
            </a>
          </p>
        ) : null}
      </section>
    </div>
  );
}
