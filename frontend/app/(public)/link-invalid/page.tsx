import Link from "next/link";

export default function LinkInvalidPage() {
  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="text-2xl font-bold">Link not available</h1>
      <p className="mt-3 text-gray-700">
        This recruiter link is no longer valid. It may have expired or been
        withdrawn. Please ask for a fresh link.
      </p>
      <p className="mt-6 text-sm">
        <Link href="/" className="underline">
          Back to start
        </Link>
      </p>
    </main>
  );
}
