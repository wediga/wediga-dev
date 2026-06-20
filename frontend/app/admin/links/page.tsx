"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { RecruiterLink, RecruiterLinkCreated } from "@/lib/types";
import {
  AdminButton,
  AdminField,
  ConfirmButton,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

function statusOf(link: RecruiterLink): string {
  if (link.revoked_at) return "Revoked";
  if (!link.active) return "Expired";
  return "Active";
}

function statusTone(status: string): string {
  if (status === "Active") return "text-success";
  if (status === "Revoked") return "text-danger";
  return "text-muted";
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
  const [createdUrl, setCreatedUrl] = useState("");
  const { run, get } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/recruiter/links", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: RecruiterLink[]) => setLinks(data));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = () =>
    run(
      "create",
      async () => {
        setCreatedUrl("");
        const body = { label: label || null, expires_on: expiresOn || null };
        const response = await apiWrite(
          "/api/recruiter/links",
          "POST",
          token,
          body,
        );
        if (response.ok) {
          const created = (await response.json()) as RecruiterLinkCreated;
          // The plaintext token is shown exactly once, right here.
          setCreatedUrl(`${window.location.origin}/r/${created.token}`);
          setLabel("");
          setExpiresOn("");
          await load();
        }
        return response.ok;
      },
      { success: "Link created", error: "Couldn't create the link. Try again." },
    );

  const revoke = (id: number) =>
    run(
      `revoke-${id}`,
      async () => {
        const response = await apiWrite(
          `/api/recruiter/links/${id}/revoke`,
          "POST",
          token,
        );
        if (response.ok) await load();
        return response.ok;
      },
      { success: "Revoked", error: "Couldn't revoke. Try again." },
    );

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Recruiter links</h1>
      <p className="mt-1 text-sm text-muted">
        Create a named magic link, share it, and see how often it was opened.
      </p>

      <div className="mt-6 max-w-md space-y-4">
        <AdminField
          label="Label"
          value={label}
          onChange={setLabel}
          placeholder="e.g. Acme Corp"
        />
        <AdminField
          label="Expires on"
          hint="Optional"
          type="date"
          value={expiresOn}
          onChange={setExpiresOn}
          className="max-w-56"
        />
        <div className="flex flex-wrap items-center gap-3">
          <AdminButton
            variant="primary"
            pending={get("create").state === "pending"}
            pendingLabel="Creating…"
            onClick={create}
          >
            Create link
          </AdminButton>
          <Feedback status={get("create")} />
        </div>
      </div>

      {createdUrl ? (
        <div className="mt-5 rounded-lg border border-status-done/40 bg-status-done/10 p-4">
          <p className="text-sm font-medium text-status-done">
            Copy this link now. It is shown only once.
          </p>
          <code className="mt-2 block break-all font-mono text-sm text-ink">
            {createdUrl}
          </code>
        </div>
      ) : null}

      <h2 className="mt-9 text-base font-semibold text-ink">Links</h2>
      <ul className="mt-3 divide-y divide-line overflow-hidden rounded-lg border border-line">
        {links.map((link) => {
          const status = statusOf(link);
          return (
            <li key={link.id} className="bg-surface/40 px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-ink">
                  {link.label || "(no label)"}
                </span>
                <span className={`text-sm font-medium ${statusTone(status)}`}>
                  {status}
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-x-6 gap-y-1 text-sm tabular-nums text-muted">
                <span>Opens: {link.view_count}</span>
                <span>Last opened: {fmt(link.last_viewed_at)}</span>
                <span>Created: {fmt(link.created_at)}</span>
                <span>
                  Expires:{" "}
                  {link.expires_at ? link.expires_at.slice(0, 10) : "never"}
                </span>
              </div>
              {link.revoked_at ? null : (
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <ConfirmButton
                    label="Revoke"
                    prompt="Revoke this link?"
                    pendingLabel="Revoking…"
                    pending={get(`revoke-${link.id}`).state === "pending"}
                    onConfirm={() => revoke(link.id)}
                  />
                  <Feedback status={get(`revoke-${link.id}`)} />
                </div>
              )}
            </li>
          );
        })}
        {links.length === 0 ? (
          <li className="bg-surface/40 px-4 py-6 text-center text-sm text-muted">
            No links yet.
          </li>
        ) : null}
      </ul>
    </div>
  );
}
