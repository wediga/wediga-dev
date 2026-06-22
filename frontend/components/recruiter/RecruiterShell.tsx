import { RecruiterNav } from "./RecruiterNav";
import { GenerativeAccents } from "./GenerativeAccents";
import { ScrollToTop } from "@/components/ScrollToTop";
import { SiteHeader, SiteFooter, ChromeLink } from "@/components/site/SiteChrome";

// The shared chrome around the three recruiter views. Dark and consistent with
// the quiet public pages, it carries navigation between the views and a way back
// to the landing (the brand wordmark). It sits inside the gate in
// (recruiter)/layout.tsx, which is untouched; this is presentation only.
//
// Layout: a sticky single-line header, a wide content area that lets each view
// use the full canvas (the views cap their own prose), and a quiet footer. The
// header and footer are the shared site chrome; the generative accent is wired
// once here for every view underneath.
export function RecruiterShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <ScrollToTop />
      <GenerativeAccents />

      <SiteHeader
        outerClassName="sticky top-0 z-[var(--z-nav)] border-b border-line bg-bg/80 backdrop-blur-md"
        rowClassName="mx-auto flex w-full max-w-[1600px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-6 py-4 sm:gap-6 lg:px-10"
        brandQuietPress
      >
        <RecruiterNav />
      </SiteHeader>

      <main className="mx-auto w-full max-w-[1600px] flex-1 px-6 pb-28 pt-[clamp(2.5rem,6vh,5rem)] lg:px-10">
        {children}
      </main>

      <SiteFooter
        outerClassName="border-t border-line"
        rowClassName="mx-auto flex w-full max-w-[1600px] items-center justify-end gap-6 px-6 py-6 text-sm text-muted-2 lg:px-10"
      >
        <ChromeLink href="/impressum">Impressum</ChromeLink>
        <ChromeLink href="/">Zur Startseite</ChromeLink>
      </SiteFooter>
    </div>
  );
}
