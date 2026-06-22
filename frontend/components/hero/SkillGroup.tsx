import type { SkillCategory } from "@/lib/types";

// One skill category: a quiet label and the skills as low-contrast tags. Tags,
// not a bulleted list, so the toolkit reads as a calm group and never as a data
// dump. The same shape renders in three places (the readable landing column, the
// full-motion toolkit station and the quiet landing), which only differ in their
// typographic scale and colour token, so those classes come in per appearance
// while the structure and the skip-empty-category guard live here once.
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
