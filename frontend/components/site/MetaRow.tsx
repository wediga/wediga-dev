/**
 * Meta row in mono muted: an availability status with an accent dot, then
 * location and stack. Wraps on narrow widths.
 */
export default function MetaRow({
  status,
  location,
  stack,
}: {
  status: string;
  location: string;
  stack: string;
}) {
  return (
    <div className="mt-8 flex flex-wrap gap-x-7 gap-y-3 font-mono text-[12.5px] text-muted-2">
      <span className="inline-flex items-center gap-2 text-ink">
        <span
          className="size-[7px] rounded-full bg-accent"
          style={{ boxShadow: "0 0 10px 1px rgba(169,135,255,0.7)" }}
          aria-hidden="true"
        />
        {status}
      </span>
      <span>{location}</span>
      <span>{stack}</span>
    </div>
  );
}
