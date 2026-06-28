"use client";

import { AdminField } from "@/components/admin/ui";
import {
  recordString,
  SingleRecordForm,
} from "@/components/admin/SingleRecordForm";

type AboutForm = { text: string };

export default function AdminAboutPage() {
  return (
    <SingleRecordForm<AboutForm>
      title="About"
      description="Markdown is rendered on the site."
      endpoint="/api/content/about"
      empty={{ text: "" }}
      fromResponse={(data) => ({ text: recordString(data.text) })}
      toBody={(value) => ({ text: value.text })}
      loadError="Couldn't load the current text. Reload the page."
      deletePrompt="Delete the intro text?"
      actionsClassName="mt-4"
    >
      {(form, update) => (
        <div className="mt-6">
          <AdminField
            label="Intro text"
            value={form.text}
            onChange={(value) => update("text", value)}
            multiline
            rows={16}
            mono
          />
        </div>
      )}
    </SingleRecordForm>
  );
}
