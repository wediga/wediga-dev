import { SiteHeader, SiteFooter, ChromeLink } from "@/components/site/SiteChrome";

// The quiet shell for the non-landing public pages (login, impressum,
// link-invalid). It carries the dark Landing surface so these read as the same
// site, but stays still and typographic: no hero, no WebGL, no ride. The route
// group does not change the URL, so the paths stay. Header and footer come from
// the shared chrome, so they cannot drift from the recruiter views or the ride.
export default function QuietLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <SiteHeader rowClassName="mx-auto flex w-full max-w-3xl items-center justify-between px-6 py-6">
        <ChromeLink href="/" className="text-sm text-muted">
          Zur Startseite
        </ChromeLink>
      </SiteHeader>

      <main className="flex flex-1 flex-col items-center justify-start px-6 pb-24 pt-[clamp(3rem,16vh,10rem)]">
        {children}
      </main>

      <SiteFooter rowClassName="mx-auto flex w-full max-w-3xl items-center justify-end gap-6 px-6 py-6 text-sm text-muted-2">
        <ChromeLink href="/impressum">Impressum</ChromeLink>
      </SiteFooter>
    </div>
  );
}
