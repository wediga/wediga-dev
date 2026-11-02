import { useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import {
  TEXT_FIELDS,
  type PortfolioEntryWrite,
  type PortfolioRepo,
  type ProjectStatus,
  type TextField,
} from "@/lib/types";
import {
  ADMIN_INPUT,
  AdminButton,
  AdminField,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

// The form of one portfolio entry: release, status, order and an own text per
// field, with the text from GitHub beside each one as the model. Only the
// client admin page imports it, so it needs no client directive of its own.

const TEXT_LABELS: Record<TextField, string> = {
  name: "Name",
  description: "Description",
  problem: "Problem",
  solution: "Solution",
  learning: "Learning",
  ending: "Why it ended",
};

function toForm(repo: PortfolioRepo, statuses: ProjectStatus[]): PortfolioEntryWrite {
  const entry = repo.entry;

  return {
    project_status_id: entry?.project_status_id ?? statuses[0]?.id ?? "",
    sort_order: entry?.sort_order ?? 0,
    published: entry?.published ?? false,
    texts: { ...entry?.texts },
  };
}

// One text: the own one to edit, the one from GitHub beside it as the model.
function TextRow({
  field,
  value,
  github,
  onChange,
}: {
  field: TextField;
  value: string;
  github: string | undefined;
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <AdminField
        label={TEXT_LABELS[field]}
        multiline={field !== "name"}
        rows={3}
        value={value}
        onChange={onChange}
        hint="Empty shows the text from GitHub"
      />
      <div>
        <p className="mb-1.5 text-[0.8125rem] font-medium text-muted">From GitHub</p>
        <p className="whitespace-pre-line text-sm text-muted">{github ?? "-"}</p>
      </div>
    </div>
  );
}

function EntryTexts({
  repo,
  texts,
  onChange,
}: {
  repo: PortfolioRepo;
  texts: PortfolioEntryWrite["texts"];
  onChange: (field: TextField, value: string) => void;
}) {
  return (
    <>
      {TEXT_FIELDS.map((field) => (
        <TextRow
          key={field}
          field={field}
          value={texts[field] ?? ""}
          github={repo.texts[field]}
          onChange={(value) => onChange(field, value)}
        />
      ))}
    </>
  );
}

function StatusSelect({
  statuses,
  value,
  onChange,
}: {
  statuses: ProjectStatus[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[0.8125rem] font-medium text-muted">
        Status
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${ADMIN_INPUT} w-full`}
      >
        {statuses.map((status) => (
          <option key={status.id} value={status.id}>
            {status.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// Release, status and order of an entry.
function EntrySettings({
  form,
  statuses,
  onChange,
}: {
  form: PortfolioEntryWrite;
  statuses: ProjectStatus[];
  onChange: (change: Partial<PortfolioEntryWrite>) => void;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="flex items-center gap-2.5 self-end pb-2.5">
        <input
          type="checkbox"
          checked={form.published}
          onChange={(event) => onChange({ published: event.target.checked })}
          className="size-4 accent-[var(--accent)]"
        />
        <span className="text-sm text-muted">Published on /portfolio</span>
      </label>
      <StatusSelect
        statuses={statuses}
        value={form.project_status_id}
        onChange={(value) => onChange({ project_status_id: value })}
      />
      <AdminField
        label="Sort order"
        type="number"
        value={String(form.sort_order)}
        onChange={(value) => onChange({ sort_order: Number(value) || 0 })}
      />
    </div>
  );
}

// Writes the entry of one repo and reloads the list after a success.
function useEntrySave(repoId: string, onSaved: () => Promise<unknown>) {
  const token = useCsrf();
  const { run, get } = useActionFeedback();

  const save = (form: PortfolioEntryWrite) =>
    run(
      "save",
      async () => {
        const path = `/api/portfolio/admin/repos/${repoId}`;
        const response = await apiWrite(path, "PUT", token, form);

        if (response.ok) await onSaved();

        return response.ok;
      },
      { success: "Saved", error: "Couldn't save. Try again." },
    );

  return { save, status: get("save") };
}

export function PortfolioEntryForm({
  repo,
  statuses,
  onSaved,
}: {
  repo: PortfolioRepo;
  statuses: ProjectStatus[];
  onSaved: () => Promise<unknown>;
}) {
  const [form, setForm] = useState(() => toForm(repo, statuses));
  const { save, status } = useEntrySave(repo.id, onSaved);
  const setText = (field: TextField, value: string) =>
    setForm((current) => ({ ...current, texts: { ...current.texts, [field]: value } }));

  return (
    <div className="mt-5 space-y-4 border-t border-line pt-5">
      <EntrySettings
        form={form}
        statuses={statuses}
        onChange={(change) => setForm((current) => ({ ...current, ...change }))}
      />
      <EntryTexts repo={repo} texts={form.texts} onChange={setText} />
      <div className="flex flex-wrap items-center gap-3">
        <AdminButton
          variant="primary"
          pending={status.state === "pending"}
          pendingLabel="Saving…"
          onClick={() => save(form)}
        >
          Save
        </AdminButton>
        <Feedback status={status} />
      </div>
    </div>
  );
}
