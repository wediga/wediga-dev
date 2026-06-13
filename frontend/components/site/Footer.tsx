import Link from "next/link";

/**
 * Footer in mono muted: the public Impressum (name and mail only, the full one
 * lives behind login), the access link and a short signature.
 */
export default function Footer() {
  return (
    <footer className="scrim relative border-t border-line px-6 py-12 font-mono text-[13px] text-muted-2 sm:px-11">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-muted">Alexander Wedig</span>
          <a
            href="mailto:hello@wediga.dev"
            className="transition-colors duration-200 hover:text-ink"
          >
            hello@wediga.dev
          </a>
        </div>
        <div className="flex gap-7">
          <Link
            href="/impressum"
            className="transition-colors duration-200 hover:text-ink"
          >
            Impressum
          </Link>
          <Link
            href="/login"
            className="transition-colors duration-200 hover:text-ink"
          >
            Access
          </Link>
        </div>
      </div>
      <p className="mt-8 text-muted-2">wediga.dev</p>
    </footer>
  );
}
