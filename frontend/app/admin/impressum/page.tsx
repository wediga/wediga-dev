"use client";

import { AdminField } from "@/components/admin/ui";
import {
  type LoadedRecord,
  recordString,
  SingleRecordForm,
} from "@/components/admin/SingleRecordForm";

type ImpressumForm = {
  name: string;
  email: string;
  github: string;
  linkedin: string;
  street: string;
  city: string;
};

const EMPTY: ImpressumForm = {
  name: "",
  email: "",
  github: "",
  linkedin: "",
  street: "",
  city: "",
};

const FIELDS: { key: keyof ImpressumForm; label: string; type?: string }[] = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email", type: "email" },
  { key: "github", label: "GitHub" },
  { key: "linkedin", label: "LinkedIn" },
  { key: "street", label: "Street" },
  { key: "city", label: "City" },
];

export default function AdminImpressumPage() {
  return (
    <SingleRecordForm<ImpressumForm>
      title="Impressum"
      description="The full legal notice behind the login."
      endpoint="/api/content/impressum"
      empty={EMPTY}
      fromResponse={(data) => {
        const address =
          typeof data.address === "object" && data.address !== null
            ? (data.address as LoadedRecord)
            : {};
        return {
          name: recordString(data.name),
          email: recordString(data.email),
          github: recordString(data.github),
          linkedin: recordString(data.linkedin),
          street: recordString(address.street),
          city: recordString(address.city),
        };
      }}
      toBody={(value) => ({
        name: value.name,
        email: value.email,
        github: value.github || null,
        linkedin: value.linkedin || null,
        address:
          value.street || value.city
            ? { street: value.street, city: value.city }
            : null,
      })}
      loadError="Couldn't load the impressum. Reload the page."
      deletePrompt="Delete the impressum?"
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
