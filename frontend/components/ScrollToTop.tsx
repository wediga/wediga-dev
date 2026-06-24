"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

// Force the window to the top on switching pages. Leaving the tall scroll-snap
// ride from a deep stop hands the next page a large scroll offset, and Next's
// automatic scroll-to-top is unreliable across the recruiter layout's async
// session gate. Resetting on each pathname change opens the gated views at top.
export function ScrollToTop() {
  const pathname = usePathname();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}
