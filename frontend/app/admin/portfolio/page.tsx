"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import { PortfolioEntryForm } from "@/components/admin/PortfolioEntryForm";
import { safeHref } from "@/lib/url";
import type { GithubSync, PortfolioAdmin, PortfolioRepo } from "@/lib/types";
import {
  AdminButton,
  EmptyState,
  Feedback,
  formatTimestamp,
  useActionFeedback,
} from "@/components/admin/ui";

// The sync owns the repos and their GitHub texts, the admin owns the entry:
// release, status, order and own texts. The list is the repos of the latest
// successful sync, a failed one leaves it as it was.
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

// What the sync knows besides the name, and the hint on a mixed tile.
function RepoFacts({ repo }: { repo: PortfolioRepo }) {
  const homepage = safeHref(repo.homepage_url);

  return (
    <>
      {repo.entry?.partly_translated ? (
        <p className="mt-2 text-sm text-danger">
          Only some texts have an own text, the tile mixes them with English from
          GitHub.
        </p>
      ) : null}
      {repo.technologies.length > 0 ? (
        <p className="mt-2 text-sm text-muted">{repo.technologies.join(" · ")}</p>
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
    </>
  );
}

function RepoItem({
  repo,
  open,
  children,
  onToggle,
}: {
  repo: PortfolioRepo;
  open: boolean;
  children: ReactNode;
  onToggle: () => void;
}) {
  const published = repo.entry?.published ?? false;

  return (
    <li className="rounded-lg border border-line bg-surface/40 p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <span className="font-medium text-ink">
          {repo.texts.name}
          <span className="ml-2 text-xs text-muted">
            {published ? "Published" : "Not published"}
            {repo.archived ? " · Archived" : ""}
          </span>
        </span>
        <AdminButton onClick={onToggle}>{open ? "Close" : "Edit"}</AdminButton>
      </div>
      <RepoFacts repo={repo} />
      {open ? children : null}
    </li>
  );
}

// Every repo with its entry, and the form of at most one of them open.
function RepoList({
  overview,
  onSaved,
}: {
  overview: PortfolioAdmin | null;
  onSaved: () => Promise<unknown>;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const repos = overview?.repos ?? [];

  if (repos.length === 0) {
    return (
      <div className="mt-6">
        <EmptyState>No repos yet. Use the sync button to fetch the public repos.</EmptyState>
      </div>
    );
  }

  return (
    <ul className="mt-6 space-y-4">
      {repos.map((repo) => (
        <RepoItem
          key={repo.id}
          repo={repo}
          open={openId === repo.id}
          onToggle={() => setOpenId(openId === repo.id ? null : repo.id)}
        >
          <PortfolioEntryForm repo={repo} statuses={overview?.statuses ?? []} onSaved={onSaved} />
        </RepoItem>
      ))}
    </ul>
  );
}

// The admin view of the portfolio, loaded once and again after every write.
function usePortfolioAdmin() {
  const [overview, setOverview] = useState<PortfolioAdmin | null>(null);
  const { get, set } = useActionFeedback();

  const load = useCallback(() => {
    return fetch("/api/portfolio/admin", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json();
      })
      .then((data: PortfolioAdmin) => setOverview(data))
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

  return { overview, load, loadStatus: get("load") };
}

// The sync reports a count on success, so it sets its own message. A 502
// means GitHub was unreachable, and the reload shows the failed run.
function SyncHeader({ onSynced }: { onSynced: () => Promise<unknown> }) {
  const token = useCsrf();
  const { get, set } = useActionFeedback();

  async function syncNow() {
    set("sync", { state: "pending" });
    const response = await apiWrite("/api/github/sync", "POST", token);
    await onSynced();

    if (response.ok) {
      const data = (await response.json()) as { synced: number };
      set("sync", { state: "success", message: `Synced ${data.synced} repos` });
    } else {
      set("sync", { state: "error", message: "Sync failed." });
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-xl font-semibold text-ink">Portfolio</h1>
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
  );
}

export default function AdminPortfolioPage() {
  const { overview, load, loadStatus } = usePortfolioAdmin();

  return (
    <div>
      <SyncHeader onSynced={load} />
      <p className="mt-1 text-sm text-muted">
        The public repos from GitHub. A published one shows as a tile, published
        ones first in their order.
      </p>
      {overview ? (
        <p className="mt-3 text-sm text-muted">
          <SyncState sync={overview.last_sync} />
        </p>
      ) : null}
      {loadStatus.state === "error" ? (
        <div className="mt-4">
          <Feedback status={loadStatus} />
        </div>
      ) : null}
      <RepoList overview={overview} onSaved={load} />
    </div>
  );
}
