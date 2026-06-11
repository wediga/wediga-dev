import { getContact } from "@/lib/content";

export default async function ContactPage() {
  const contact = await getContact();

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold">Contact</h1>
      {contact ? (
        <dl className="mt-4 space-y-2">
          <div>
            <dt className="text-sm text-gray-500">Name</dt>
            <dd>{contact.name}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Email</dt>
            <dd>
              <a href={`mailto:${contact.email}`} className="underline">
                {contact.email}
              </a>
            </dd>
          </div>
          {contact.github ? (
            <div>
              <dt className="text-sm text-gray-500">GitHub</dt>
              <dd>
                <a
                  href={contact.github}
                  className="underline"
                  rel="noreferrer noopener"
                >
                  {contact.github}
                </a>
              </dd>
            </div>
          ) : null}
          {contact.linkedin ? (
            <div>
              <dt className="text-sm text-gray-500">LinkedIn</dt>
              <dd>
                <a
                  href={contact.linkedin}
                  className="underline"
                  rel="noreferrer noopener"
                >
                  {contact.linkedin}
                </a>
              </dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="mt-2 text-gray-500">No contact details yet.</p>
      )}
    </main>
  );
}
