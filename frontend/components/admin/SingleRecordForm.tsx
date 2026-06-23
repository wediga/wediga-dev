"use client";

// The shared scaffold for the three single-record content pages (about,
// contact, impressum). Each of them is the same form around a single backend
// record: load it on mount, edit it in place, save with one primary write, and
// delete it behind an inline confirmation. The only per-page differences are
// the fields, the endpoint, and the messages, so those are passed as config and
// the fields are rendered through a children render-prop.

import { type ReactNode, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import {
  AdminButton,
  ConfirmButton,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

// The parsed GET body. The single-record endpoints return free-form JSON whose
// shape each page knows, so it is read as a loose, nested record and the page's
// fromResponse picks the fields it needs.
export type LoadedRecord = {
  [key: string]: string | number | boolean | null | undefined | LoadedRecord;
};

// Read one record value as the string the text fields expect, with the same
// "missing becomes empty" result the pages relied on before.
export function recordString(value: LoadedRecord[string]): string {
  return typeof value === "string" ? value : "";
}

type SingleRecordFormProps<T> = {
  title: string;
  description: string;
  endpoint: string;
  empty: T;
  // Only applied when the GET response is ok; a non-ok response leaves the
  // empty state, matching the per-page behaviour before this scaffold.
  fromResponse: (data: LoadedRecord) => T;
  toBody: (value: T) => unknown;
  loadError: string;
  deletePrompt: string;
  // Spacing of the footer differs per page (about uses mt-4, the two-column
  // forms use mt-5), so it is threaded through rather than hard-coded.
  actionsClassName?: string;
  children: (
    form: T,
    update: <K extends keyof T>(key: K, value: T[K]) => void,
  ) => ReactNode;
};

export function SingleRecordForm<T>({
  title,
  description,
  endpoint,
  empty,
  fromResponse,
  toBody,
  loadError,
  deletePrompt,
  actionsClassName = "mt-5",
  children,
}: SingleRecordFormProps<T>) {
  const token = useCsrf();
  const [form, setForm] = useState<T>(empty);
  const { run, get, set } = useActionFeedback();

  useEffect(() => {
    fetch(endpoint, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data) setForm(fromResponse(data));
      })
      .catch(() => set("load", { state: "error", message: loadError }));
    // The config is stable per page; only the feedback setter is a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [set]);

  function update<K extends keyof T>(key: K, value: T[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  const save = () =>
    run(
      "save",
      async () => {
        const response = await apiWrite(endpoint, "PUT", token, toBody(form));
        return response.ok;
      },
      { success: "Saved", error: "Couldn't save. Try again." },
    );

  const remove = () =>
    run(
      "delete",
      async () => {
        const response = await apiWrite(endpoint, "DELETE", token);
        if (response.ok) setForm(empty);
        return response.ok;
      },
      { success: "Deleted", error: "Couldn't delete. Try again." },
    );

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">{title}</h1>
      <p className="mt-1 text-sm text-muted">{description}</p>
      {get("load").state === "error" ? (
        <div className="mt-4">
          <Feedback status={get("load")} />
        </div>
      ) : null}

      {children(form, update)}

      <div className={`${actionsClassName} flex flex-wrap items-center gap-3`}>
        <AdminButton
          variant="primary"
          pending={get("save").state === "pending"}
          pendingLabel="Saving…"
          onClick={save}
        >
          Save
        </AdminButton>
        <ConfirmButton
          label="Delete"
          prompt={deletePrompt}
          pendingLabel="Deleting…"
          pending={get("delete").state === "pending"}
          onConfirm={remove}
        />
        <Feedback status={get("save")} />
        <Feedback status={get("delete")} />
      </div>
    </div>
  );
}
