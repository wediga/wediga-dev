"use client";

import { useCallback, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import type { GithubRepo } from "@/lib/types";

// Only the four curation fields are editable; the mirrored GitHub fields are
// shown read-only. The sync refreshes the mirrored fields and never touches
// the curation, so edits here survive every refresh.
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
  const [status, setStatus] = useState("");
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(() => {
    return fetch("/api/github/repos", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((data: GithubRepo[]) => {
        setRepos(data);
        setEdits(
          Object.fromEntries(data.map((repo) => [repo.id, toCuration(repo)])),
        );
      });
  }, []);

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

  async function save(id: number) {
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
    if (response.ok) {
      setStatus("Saved");
      await load();
    } else {
      setStatus("Save failed");
    }
  }

  async function syncNow() {
    setSyncing(true);
    setStatus("");
    const response = await apiWrite("/api/github/sync", "POST", token);
    setSyncing(false);
    if (response.ok) {
      const data = (await response.json()) as { synced: number };
      setStatus(`Synced ${data.synced} repos`);
      await load();
    } else {
      // A 502 means GitHub was unreachable; the existing cache is unchanged.
      setStatus("Sync failed; the existing list is unchanged");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">GitHub repos</h1>
        <button
          onClick={syncNow}
          disabled={syncing}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {syncing ? "Syncing..." : "Sync now"}
        </button>
      </div>
      <p className="mt-2 text-gray-600">
        The sync mirrors the public repos. Curate them here: hide, pin, override
        the description and order them. Curation is kept across every sync.
      </p>
      {status ? (
        <p className="mt-2 text-sm text-gray-600">{status}</p>
      ) : null}

      <ul className="mt-6 space-y-4">
        {repos.map((repo) => {
          const edit = edits[repo.id];
          if (!edit) return null;
          return (
            <li key={repo.id} className="rounded border border-gray-200 p-4">
              <div className="flex items-baseline justify-between">
                <span className="font-semibold">{repo.name}</span>
                <span className="text-sm text-gray-500">
                  {repo.language ?? "-"} · {repo.stars ?? 0}★
                </span>
              </div>
              {repo.description ? (
                <p className="mt-1 text-sm text-gray-600">{repo.description}</p>
              ) : null}

              <div className="mt-3 flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={edit.visible}
                    onChange={(event) =>
                      update(repo.id, "visible", event.target.checked)
                    }
                  />
                  <span className="text-sm text-gray-600">visible</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={edit.pinned}
                    onChange={(event) =>
                      update(repo.id, "pinned", event.target.checked)
                    }
                  />
                  <span className="text-sm text-gray-600">pinned</span>
                </label>
                <label className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">sort</span>
                  <input
                    type="number"
                    value={edit.sort_order}
                    onChange={(event) =>
                      update(repo.id, "sort_order", Number(event.target.value))
                    }
                    className="w-20 rounded border border-gray-300 px-2 py-1"
                  />
                </label>
              </div>

              <label className="mt-3 block">
                <span className="text-sm text-gray-600">
                  description override (optional)
                </span>
                <input
                  value={edit.description_override}
                  onChange={(event) =>
                    update(repo.id, "description_override", event.target.value)
                  }
                  placeholder={repo.description ?? ""}
                  className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
                />
              </label>

              <button
                onClick={() => save(repo.id)}
                className="mt-3 rounded border border-gray-300 px-3 py-1 text-sm"
              >
                Save
              </button>
            </li>
          );
        })}
        {repos.length === 0 ? (
          <li className="rounded border border-gray-200 px-4 py-3 text-sm text-gray-500">
            No repos yet. Use the sync button to fetch the public repos.
          </li>
        ) : null}
      </ul>
    </div>
  );
}
