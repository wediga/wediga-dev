import { getCvStatus } from "@/lib/content";

// The recruiter CV view. The CV is a single uploaded PDF, so this page offers
// the download and an inline preview of that same file. Both load the gated
// backend download route through the BFF. The final visual design lands in the
// separate visual relaunch; this follows the page design functionally.
export default async function CvPage() {
  const { present } = await getCvStatus();

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold tracking-wide text-gray-900">CV</h1>

      {present ? (
        <>
          <a
            href="/api/cv/download"
            className="mt-5 inline-block rounded bg-gray-900 px-4 py-2 text-sm text-white"
          >
            Download as PDF
          </a>
          <object
            data="/api/cv/download?inline=1"
            type="application/pdf"
            className="mt-6 h-[80vh] w-full rounded border border-gray-200"
            aria-label="CV preview"
          >
            <p className="p-4 text-sm text-gray-600">
              The preview cannot be shown. Use the download above.
            </p>
          </object>
        </>
      ) : (
        <p className="mt-2 text-gray-600">No CV available yet.</p>
      )}
    </main>
  );
}
