import type { Metadata, Viewport } from "next";
import { Familjen_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { MOTION_INIT_SCRIPT } from "@/lib/motion";

const display = Familjen_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "wediga.dev",
  description: "Personal portfolio site",
};

// Without this, mobile browsers render at a ~980px desktop layout viewport and
// scale it down, so the page looks tiny and off-screen and the compact media
// query (max-width / pointer) can resolve wrong. width=device-width maps the
// layout viewport to the real device width, which is what makes the responsive
// breakpoints and the mobile quiet-motion default actually fire on a phone.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${plexMono.variable} h-full antialiased`}
      // The init script sets data-motion before paint, so the attribute is
      // already on the element React hydrates against; suppress the resulting
      // attribute mismatch on this one node.
      suppressHydrationWarning
    >
      <head>
        {/* Resolve the motion mode before first paint to avoid a flash: a stored
            choice wins over the OS prefers-reduced-motion, which wins over the
            full-motion default. Mirrors resolveMotion in lib/motion.ts. */}
        <script dangerouslySetInnerHTML={{ __html: MOTION_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
