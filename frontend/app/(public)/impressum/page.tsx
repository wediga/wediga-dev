import { getImpressum } from "@/lib/content";

// The public impressum shows only name and email. The full legal details
// (address and links) sit behind the recruiter view, which the later phase
// gates by session.
export default async function ImpressumPage() {
  const impressum = await getImpressum();

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold">Impressum</h1>
      {impressum ? (
        <dl className="mt-4 space-y-2">
          <div>
            <dt className="text-sm text-gray-500">Name</dt>
            <dd>{impressum.name}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Email</dt>
            <dd>{impressum.email}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-2 text-gray-500">No legal notice yet.</p>
      )}
    </main>
  );
}
