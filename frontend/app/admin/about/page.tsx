"use client";

import { useEffect, useState } from "react";
import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import {
  AdminButton,
  AdminField,
  ConfirmButton,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

export default function AdminAboutPage() {
  const token = useCsrf();
  const [text, setText] = useState("");
  const { run, get, set } = useActionFeedback();

  useEffect(() => {
    fetch("/api/content/about", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : { text: "" }))
      .then((data) => setText(data.text ?? ""))
      .catch(() =>
        set("load", {
          state: "error",
          message: "Couldn't load the current text. Reload the page.",
        }),
      );
  }, [set]);

  const save = () =>
    run(
      "save",
      async () => {
        const response = await apiWrite("/api/content/about", "PUT", token, {
          text,
        });
        return response.ok;
      },
      { success: "Saved", error: "Couldn't save. Try again." },
    );

  const remove = () =>
    run(
      "delete",
      async () => {
        const response = await apiWrite("/api/content/about", "DELETE", token);
        if (response.ok) setText("");
        return response.ok;
      },
      { success: "Deleted", error: "Couldn't delete. Try again." },
    );

  const load = get("load");
  const saving = get("save").state === "pending";

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">About</h1>
      <p className="mt-1 text-sm text-muted">
        Markdown is rendered on the site.
      </p>
      {load.state === "error" ? (
        <p className="mt-4 text-sm text-danger">{load.message}</p>
      ) : null}

      <div className="mt-6">
        <AdminField
          label="Intro text"
          value={text}
          onChange={setText}
          multiline
          rows={16}
          mono
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <AdminButton
          variant="primary"
          pending={saving}
          pendingLabel="Saving…"
          onClick={save}
        >
          Save
        </AdminButton>
        <ConfirmButton
          label="Delete"
          prompt="Delete the intro text?"
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
