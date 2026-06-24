import type { SkillCategory } from "@/lib/types";

// One skill category: a label and the skills as tags, not a bulleted list, so the
// toolkit reads as a group not a data dump. The same shape renders in the readable
// column, the toolkit station and the quiet landing, which differ only in scale
// and colour token, so those classes come in per appearance while the structure
// and the skip-empty-category guard live here once.
export function SkillGroup({
  category,
  labelClass,
  listClass,
  pillClass,
}: {
  category: SkillCategory;
  labelClass: string;
  listClass: string;
  pillClass: string;
}) {
  if (category.skills.length === 0) return null;
  return (
    <div>
      <p className={labelClass}>{category.name}</p>
      <ul className={listClass}>
        {category.skills.map((skill) => (
          <li key={skill.id} className={pillClass}>
            {skill.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
