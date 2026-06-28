"use client";

import { AdminField } from "@/components/admin/ui";
import {
  recordString,
  SingleRecordForm,
} from "@/components/admin/SingleRecordForm";

type ContactForm = {
  name: string;
  email: string;
  github: string;
  linkedin: string;
};

const FIELDS: { key: keyof ContactForm; label: string; type?: string }[] = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email", type: "email" },
  { key: "github", label: "GitHub" },
  { key: "linkedin", label: "LinkedIn" },
];

export default function AdminContactPage() {
  return (
    <SingleRecordForm<ContactForm>
      title="Contact"
      description="Shown on the protected contact view."
      endpoint="/api/content/contact"
      empty={{ name: "", email: "", github: "", linkedin: "" }}
      fromResponse={(data) => ({
        name: recordString(data.name),
        email: recordString(data.email),
        github: recordString(data.github),
        linkedin: recordString(data.linkedin),
      })}
      toBody={(value) => ({
        name: value.name,
        email: value.email,
        github: value.github || null,
        linkedin: value.linkedin || null,
      })}
      loadError="Couldn't load the contact details. Reload the page."
      deletePrompt="Delete the contact details?"
    >
      {(form, update) => (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {FIELDS.map((field) => (
            <AdminField
              key={field.key}
              label={field.label}
              type={field.type}
              value={form[field.key]}
              onChange={(value) => update(field.key, value)}
            />
          ))}
        </div>
      )}
    </SingleRecordForm>
  );
}
