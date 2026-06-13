import type { ReactNode } from "react";

/**
 * Large Familjen Grotesk display headline. Tight tracking and balanced wrapping,
 * sized down for h2 so the hierarchy reads through weight and scale, not boxes.
 */
export default function DisplayHeading({
  children,
  as = "h1",
}: {
  children: ReactNode;
  as?: "h1" | "h2";
}) {
  const Tag = as;
  const isHero = as === "h1";
  return (
    <Tag
      className={
        isHero
          ? "font-sans font-bold leading-[0.94] tracking-[-0.03em] text-ink"
          : "font-sans font-semibold leading-tight tracking-[-0.02em] text-ink"
      }
      style={{
        textWrap: "balance",
        fontSize: isHero
          ? "clamp(3.25rem, 9vw, 6.5rem)"
          : "clamp(1.5rem, 2.8vw, 1.875rem)",
      }}
    >
      {children}
    </Tag>
  );
}
