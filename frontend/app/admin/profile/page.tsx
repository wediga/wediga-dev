"use client";

import { AdminField } from "@/components/admin/ui";
import {
  type LoadedRecord,
  recordString,
  SingleRecordForm,
} from "@/components/admin/SingleRecordForm";
import { LINK_LABELS, type LinkKind, type ProfileLinks } from "@/lib/types";

type ProfileForm = {
  name: string;
  email: string;
  links: ProfileLinks;
  street: string;
  postal_code: string;
  city: string;
  about_md: string;
};

const EMPTY: ProfileForm = {
  name: "",
  email: "",
  links: {},
  street: "",
  postal_code: "",
  city: "",
  about_md: "",
};

const LINK_KINDS = Object.keys(LINK_LABELS) as LinkKind[];

const ADDRESS_FIELDS: { key: "street" | "postal_code" | "city"; label: string }[] =
  [
    { key: "street", label: "Street" },
    { key: "postal_code", label: "Postal code" },
    { key: "city", label: "City" },
  ];

function asRecord(value: LoadedRecord[string]): LoadedRecord {
  return typeof value === "object" && value !== null ? value : {};
}

export default function AdminProfilePage() {
  return (
    <SingleRecordForm<ProfileForm>
      title="Profile"
      description="The contact page and the public impressum are built from this record. The address stays in the admin area."
      endpoint="/api/content/profile"
      empty={EMPTY}
      fromResponse={(data) => {
        const links = asRecord(data.links);
        const address = asRecord(data.address);

        return {
          name: recordString(data.name),
          email: recordString(data.email),
          links: Object.fromEntries(
            LINK_KINDS.map((kind) => [kind, recordString(links[kind])]),
          ),
          street: recordString(address.street),
          postal_code: recordString(address.postal_code),
          city: recordString(address.city),
          about_md: recordString(data.about_md),
        };
      }}
      toBody={(value) => ({
        name: value.name,
        email: value.email,
        about_md: value.about_md,
        links: Object.fromEntries(
          Object.entries(value.links).filter(([, url]) => url),
        ),
        address:
          value.street || value.postal_code || value.city
            ? {
                street: value.street,
                postal_code: value.postal_code,
                city: value.city,
              }
            : null,
      })}
      loadError="Couldn't load the profile. Reload the page."
    >
      {(form, update) => (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <AdminField
              label="Name"
              value={form.name}
              onChange={(value) => update("name", value)}
            />
            <AdminField
              label="Email"
              type="email"
              value={form.email}
              onChange={(value) => update("email", value)}
            />
            {LINK_KINDS.map((kind) => (
              <AdminField
                key={kind}
                label={LINK_LABELS[kind]}
                value={form.links[kind] ?? ""}
                onChange={(value) =>
                  update("links", { ...form.links, [kind]: value })
                }
              />
            ))}
            {ADDRESS_FIELDS.map((field) => (
              <AdminField
                key={field.key}
                label={field.label}
                value={form[field.key]}
                onChange={(value) => update(field.key, value)}
              />
            ))}
          </div>
          <div className="mt-6">
            <AdminField
              label="About (Markdown)"
              value={form.about_md}
              onChange={(value) => update("about_md", value)}
              multiline
              rows={16}
              mono
            />
          </div>
        </>
      )}
    </SingleRecordForm>
  );
}
