"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import { safeHref } from "@/lib/url";
import type { GithubOverview, GithubRepo, GithubSync } from "@/lib/types";
import {
  AdminButton,
  EmptyState,
  Feedback,
  formatTimestamp,
  useActionFeedback,
} from "@/components/admin/ui";

// The sync owns everything shown here, so the page only reads it. The list is
// the repos of the latest successful sync, a failed one leaves it as it was.
function SyncState({ sync }: { sync: GithubSync | null }) {
  if (!sync) return <>No sync yet.</>;

  const started = formatTimestamp(sync.started_at);

  if (sync.error) {
    return (
      <span className="text-danger">
        The sync at {started} failed: {sync.error}. The list shows the last
        successful sync.
      </span>
    );
  }

  if (!sync.finished_at) return <>A sync is running since {started}.</>;

  return <>Last sync: {started}</>;
}

function RepoItem({ repo }: { repo: GithubRepo }) {
  const homepage = safeHref(repo.homepage_url);

  return (
    <li className="rounded-lg border border-line bg-surface/40 p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-medium text-ink">{repo.name}</span>
        {repo.archived ? (
          <span className="text-sm text-muted">Archived</span>
        ) : null}
      </div>
      {repo.description ? (
        <p className="mt-1 text-sm text-muted">{repo.description}</p>
      ) : null}
      {repo.technologies.length > 0 ? (
        <p className="mt-2 text-sm text-muted">
          {repo.technologies.join(" · ")}
        </p>
      ) : null}
      {homepage ? (
        <a
          href={homepage}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-sm text-accent underline-offset-4 hover:underline"
        >
          {repo.homepage_url}
        </a>
      ) : null}
    </li>
  );
}

export default function AdminReposPage() {
  const token = useCsrf();
  const [overview, setOverview] = useState<GithubOverview | null>(null);
  const { get, set } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/github/repos", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json();
      })
      .then((data: GithubOverview) => setOverview(data))
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

  // The sync reports a count on success, so it sets its own message. A 502
  // means GitHub was unreachable, and the reload shows the failed run.
  async function syncNow() {
    set("sync", { state: "pending" });
    const response = await apiWrite("/api/github/sync", "POST", token);
    await load();

    if (response.ok) {
      const data = (await response.json()) as { synced: number };
      set("sync", { state: "success", message: `Synced ${data.synced} repos` });
    } else {
      set("sync", { state: "error", message: "Sync failed." });
    }
  }

  const repos = overview?.repos ?? [];

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
        The public repos as the sync reads them from GitHub, with their topics.
      </p>
      {overview ? (
        <p className="mt-3 text-sm text-muted">
          <SyncState sync={overview.last_sync} />
        </p>
      ) : null}
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
          {repos.map((repo) => (
            <RepoItem key={repo.id} repo={repo} />
          ))}
        </ul>
      )}
    </div>
  );
}
