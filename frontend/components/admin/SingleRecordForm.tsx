// Scaffold for a single-record content page: load on mount, edit in place and
// save with one write. The fields, endpoint and messages are passed as config
// and the fields render through a children prop. It has no "use client" of its
// own because it takes functions as props and only runs inside client pages.

import { type ReactNode, useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import { AdminButton, Feedback, useActionFeedback } from "@/components/admin/ui";

// The single-record endpoints return free-form nested JSON whose shape each page
// knows, so it is read loosely and the page's fromResponse picks what it needs.
export type LoadedRecord = {
  [key: string]: string | number | boolean | null | undefined | LoadedRecord;
};

// Read one value as the string the text fields expect; missing becomes empty.
export function recordString(value: LoadedRecord[string]): string {
  return typeof value === "string" ? value : "";
}

type SingleRecordFormProps<T> = {
  title: string;
  description: string;
  endpoint: string;
  empty: T;
  // Applied only on an ok GET; a non-ok response leaves the empty state.
  fromResponse: (data: LoadedRecord) => T;
  toBody: (value: T) => unknown;
  loadError: string;
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
    // Config is stable per page; only the feedback setter is a dependency.
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

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <AdminButton
          variant="primary"
          pending={get("save").state === "pending"}
          pendingLabel="Saving…"
          onClick={save}
        >
          Save
        </AdminButton>
        <Feedback status={get("save")} />
      </div>
    </div>
  );
}
