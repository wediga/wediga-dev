"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { GithubRepo } from "@/lib/types";
import {
  AdminButton,
  AdminField,
  EmptyState,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

// Only the four curation fields are editable; the mirrored GitHub fields are
// read-only. The sync refreshes the mirrored fields and never touches curation,
// so edits here survive every refresh.
type Curation = {
  visible: boolean;
  pinned: boolean;
  description_override: string;
  sort_order: number;
};

function toCuration(repo: GithubRepo): Curation {
  return {
    visible: repo.visible,
    pinned: repo.pinned,
    description_override: repo.description_override ?? "",
    sort_order: repo.sort_order,
  };
}

export default function AdminReposPage() {
  const token = useCsrf();
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [edits, setEdits] = useState<Record<number, Curation>>({});
  const { run, get, set } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/github/repos", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: GithubRepo[]) => {
        setRepos(data);
        setEdits(
          Object.fromEntries(data.map((repo) => [repo.id, toCuration(repo)])),
        );
      })
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't load the repos. Reload the page.",
        }),
      );
  }, [set]);

  useEffect(() => {
    load();
  }, [load]);

  function update<K extends keyof Curation>(
    id: number,
    field: K,
    value: Curation[K],
  ) {
    setEdits((current) => ({
      ...current,
      [id]: { ...current[id], [field]: value },
    }));
  }

  const save = (id: number) =>
    run(
      `repo-${id}`,
      async () => {
        const edit = edits[id];
        const body = {
          visible: edit.visible,
          pinned: edit.pinned,
          description_override: edit.description_override || null,
          sort_order: Number(edit.sort_order) || 0,
        };
        const response = await apiWrite(
          `/api/github/repos/${id}/curation`,
          "PUT",
          token,
          body,
        );
        if (response.ok) await load();
        return response.ok;
      },
      { success: "Saved", error: "Couldn't save. Try again." },
    );

  // The sync reports a count on success, so it sets its own message. A 502 means
  // GitHub was unreachable and the cache is left unchanged.
  async function syncNow() {
    set("sync", { state: "pending" });
    const response = await apiWrite("/api/github/sync", "POST", token);
    if (response.ok) {
      const data = (await response.json()) as { synced: number };
      await load();
      set("sync", {
        state: "success",
        message: `Synced ${data.synced} repos`,
      });
    } else {
      set("sync", {
        state: "error",
        message: "Sync failed; the existing list is unchanged.",
      });
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-ink">GitHub repos</h1>
        <div className="flex items-center gap-3">
          <Feedback status={get("sync")} pendingLabel="Syncing…" />
          <AdminButton
            variant="primary"
            pending={get("sync").state === "pending"}
            pendingLabel="Syncing…"
            onClick={syncNow}
          >
            Sync now
          </AdminButton>
        </div>
      </div>
      <p className="mt-1 text-sm text-muted">
        The sync mirrors the public repos. Curate them here: hide, pin, override
        the description and order them. Curation is kept across every sync.
      </p>
      {get("load").state === "error" ? (
        <div className="mt-4">
          <Feedback status={get("load")} />
        </div>
      ) : null}

      {repos.length === 0 ? (
        <div className="mt-6">
          <EmptyState>
            No repos yet. Use the sync button to fetch the public repos.
          </EmptyState>
        </div>
      ) : (
        <ul className="mt-6 space-y-4">
          {repos.map((repo) => {
          const edit = edits[repo.id];
          if (!edit) return null;
          return (
            <li
              key={repo.id}
              className="rounded-lg border border-line bg-surface/40 p-4 sm:p-5"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-medium text-ink">{repo.name}</span>
                <span className="text-sm tabular-nums text-muted">
                  {repo.language ?? "-"} · {repo.stars ?? 0}★
                </span>
              </div>
              {repo.description ? (
                <p className="mt-1 text-sm text-muted">{repo.description}</p>
              ) : null}

              <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
                <label className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={edit.visible}
                    onChange={(event) =>
                      update(repo.id, "visible", event.target.checked)
                    }
                    className="size-4 accent-[var(--accent)]"
                  />
                  <span className="text-sm text-muted">Visible</span>
                </label>
                <label className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={edit.pinned}
                    onChange={(event) =>
                      update(repo.id, "pinned", event.target.checked)
                    }
                    className="size-4 accent-[var(--accent)]"
                  />
                  <span className="text-sm text-muted">Pinned</span>
                </label>
                <label className="flex items-center gap-2.5">
                  <span className="text-sm text-muted">Sort</span>
                  <input
                    type="number"
                    value={edit.sort_order}
                    onChange={(event) =>
                      update(repo.id, "sort_order", Number(event.target.value))
                    }
                    aria-label="Sort order"
                    className="w-20 rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm tabular-nums text-ink transition-colors duration-150 ease-out hover:border-muted-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60"
                  />
                </label>
              </div>

              <div className="mt-4">
                <AdminField
                  label="Description override"
                  hint="Optional, replaces the mirrored description on the site"
                  value={edit.description_override}
                  placeholder={repo.description ?? ""}
                  onChange={(value) =>
                    update(repo.id, "description_override", value)
                  }
                />
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <AdminButton
                  pending={get(`repo-${repo.id}`).state === "pending"}
                  pendingLabel="Saving…"
                  onClick={() => save(repo.id)}
                >
                  Save
                </AdminButton>
                <Feedback status={get(`repo-${repo.id}`)} />
              </div>
            </li>
          );
          })}
        </ul>
      )}
    </div>
  );
}
