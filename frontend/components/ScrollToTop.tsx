"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

// Force the window to the top on entering or switching pages. The landing hero
// is a tall scroll-snap ride, so leaving it from a deep stop hands the next page
// a large scroll offset, and Next's automatic scroll-to-top is unreliable across
// the recruiter layout's async session gate. Resetting on each pathname change
// keeps the gated views opening at their top instead of mid-page.
export function ScrollToTop() {
  const pathname = usePathname();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}
