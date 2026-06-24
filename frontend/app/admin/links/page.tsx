"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { RecruiterLink, RecruiterLinkCreated } from "@/lib/types";
import {
  AdminButton,
  AdminField,
  ConfirmButton,
  EmptyState,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

// Label and tone are derived together, so the rendered word and its colour
// cannot drift apart.
function linkStatus(link: RecruiterLink): { label: string; tone: string } {
  if (link.revoked_at) return { label: "Revoked", tone: "text-danger" };
  if (!link.active) return { label: "Expired", tone: "text-muted" };
  return { label: "Active", tone: "text-success" };
}

// Short readable timestamp without a date library.
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
  const { run, get, set } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/recruiter/links", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: RecruiterLink[]) => setLinks(data))
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't load the links. Reload the page.",
        }),
      );
  }, [set]);

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
          // The plaintext token is shown exactly once, here.
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
      {get("load").state === "error" ? (
        <div className="mt-4">
          <Feedback status={get("load")} />
        </div>
      ) : null}

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
      {links.length === 0 ? (
        <div className="mt-3">
          <EmptyState>No links yet.</EmptyState>
        </div>
      ) : (
        <ul className="mt-3 divide-y divide-line overflow-hidden rounded-lg border border-line">
          {links.map((link) => {
            const status = linkStatus(link);
            return (
              <li key={link.id} className="bg-surface/40 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-ink">
                    {link.label || "(no label)"}
                  </span>
                  <span className={`text-sm font-medium ${status.tone}`}>
                    {status.label}
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
        </ul>
      )}
    </div>
  );
}
