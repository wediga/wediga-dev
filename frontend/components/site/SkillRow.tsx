/**
 * A list row: the group label on the left, the tools on the right, separated by
 * a fine top rule. No pill tags, hierarchy comes from the rules and the type.
 * Stack the group and tools in the layout (a list of these reads as a table).
 */
export default function SkillRow({
  group,
  tools,
}: {
  group: string;
  tools: string;
}) {
  return (
    <div className="grid grid-cols-1 items-baseline gap-2 border-t border-line py-[18px] sm:grid-cols-[200px_1fr] sm:gap-7">
      <div className="font-mono text-[13px] text-muted-2">{group}</div>
      <div className="text-[18px] text-ink">{tools}</div>
    </div>
  );
}
