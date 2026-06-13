/**
 * Recurring node-edge divider: a small glowing accent node, an outgoing line
 * that fades to nothing and a short mono label. The brand motif that ties the
 * cosmos to the content.
 */
export default function NodeEdge({ label }: { label: string }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <span
        className="size-[7px] shrink-0 rounded-full bg-accent"
        style={{ boxShadow: "0 0 10px 1px rgba(169,135,255,0.6)" }}
        aria-hidden="true"
      />
      <span className="font-mono text-xs uppercase tracking-[0.12em] text-muted-2">
        {label}
      </span>
      <span
        className="h-px flex-1"
        style={{
          background:
            "linear-gradient(90deg, rgba(169,135,255,0.45), rgba(198,200,220,0.12) 26%, transparent 70%)",
        }}
        aria-hidden="true"
      />
    </div>
  );
}
