"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { RecruiterLink, RecruiterLinkCreated } from "@/lib/types";

function statusOf(link: RecruiterLink): string {
  if (link.revoked_at) return "Revoked";
  if (!link.active) return "Expired";
  return "Active";
}

// Show a timestamp as a short, readable value without pulling in a date library.
function fmt(value: string | null): string {
  if (!value) return "-";
  return value.slice(0, 16).replace("T", " ");
}

export default function AdminLinksPage() {
  const token = useCsrf();
  const [links, setLinks] = useState<RecruiterLink[]>([]);
  const [label, setLabel] = useState("");
  const [expiresOn, setExpiresOn] = useState("");
  const [status, setStatus] = useState("");
  const [createdUrl, setCreatedUrl] = useState("");

  const load = useCallback(() => {
    return fetch("/api/recruiter/links", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: RecruiterLink[]) => setLinks(data));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function create() {
    setStatus("");
    setCreatedUrl("");
    const body = {
      label: label || null,
      expires_on: expiresOn || null,
    };
    const response = await apiWrite("/api/recruiter/links", "POST", token, body);
    if (response.ok) {
      const created = (await response.json()) as RecruiterLinkCreated;
      // The plaintext token is shown exactly once, right here.
      setCreatedUrl(`${window.location.origin}/r/${created.token}`);
      setLabel("");
      setExpiresOn("");
      await load();
    } else {
      setStatus("Create failed");
    }
  }

  async function revoke(id: number) {
    const response = await apiWrite(
      `/api/recruiter/links/${id}/revoke`,
      "POST",
      token,
    );
    if (response.ok) {
      await load();
    } else {
      setStatus("Revoke failed");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Recruiter links</h1>
      <p className="mt-2 text-gray-600">
        Create a named magic link, share it, and see how often it was opened.
      </p>

      <div className="mt-6 space-y-3">
        <label className="block">
          <span className="text-sm text-gray-600">Label</span>
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="e.g. Acme Corp"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block">
          <span className="text-sm text-gray-600">Expires on (optional)</span>
          <input
            type="date"
            value={expiresOn}
            onChange={(event) => setExpiresOn(event.target.value)}
            className="mt-1 w-48 rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <button
          onClick={create}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white"
        >
          Create link
        </button>
        {status ? <span className="ml-3 text-sm text-gray-600">{status}</span> : null}
      </div>

      {createdUrl ? (
        <div className="mt-4 rounded border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-900">
            Copy this link now. It is shown only once.
          </p>
          <code className="mt-2 block break-all text-sm">{createdUrl}</code>
        </div>
      ) : null}

      <h2 className="mt-8 text-lg font-semibold">Links</h2>
      <ul className="mt-3 divide-y divide-gray-200 rounded border border-gray-200">
        {links.map((link) => (
          <li key={link.id} className="px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="font-medium">{link.label || "(no label)"}</span>
              <span className="text-sm text-gray-500">{statusOf(link)}</span>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600">
              <span>Opens: {link.view_count}</span>
              <span>Last opened: {fmt(link.last_viewed_at)}</span>
              <span>Created: {fmt(link.created_at)}</span>
              <span>
                Expires: {link.expires_at ? link.expires_at.slice(0, 10) : "never"}
              </span>
            </div>
            {link.revoked_at ? null : (
              <button
                onClick={() => revoke(link.id)}
                className="mt-2 rounded border border-gray-300 px-3 py-1 text-sm"
              >
                Revoke
              </button>
            )}
          </li>
        ))}
        {links.length === 0 ? (
          <li className="px-4 py-2 text-sm text-gray-500">No links yet.</li>
        ) : null}
      </ul>
    </div>
  );
}
