"""Idempotent seed of database content from the content directory.

Reads the content files and upserts them on a stable natural key, so a re-run
makes no duplicates and pulls in file edits, never writing back to the files.
The admin-managed ``visible`` flag on a project survives a re-seed, so it never
re-shows a project the admin hid. The summary counts entries processed, not
rows changed.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.content import repository
from app.content.models import Project, Skill, SkillCategory
from app.db.connection import get_session
from app.paths import content_dir

# The project columns a re-seed overwrites. ``visible`` is absent because it
# belongs to the admin.
_PROJECT_FILE_COLUMNS = (
    "tagline",
    "problem",
    "solution",
    "learning",
    "tech_stack",
    "demo_link",
    "github_link",
    "status",
    "sort_order",
)


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"content file missing: {path}")
    return path


def _seed_about(session: Session, base: Path) -> int:
    path = _require(base / "about.md")
    text = path.read_text(encoding="utf-8")
    repository._set_setting(session, "about_text", text)
    return 1


def _seed_setting_json(session: Session, base: Path, filename: str, key: str) -> int:
    path = _require(base / filename)
    data = json.loads(path.read_text(encoding="utf-8"))
    repository._set_setting(session, key, json.dumps(data, ensure_ascii=False))
    return 1


def _seed_projects(session: Session, base: Path) -> int:
    path = _require(base / "projects.json")
    projects = json.loads(path.read_text(encoding="utf-8"))

    for index, item in enumerate(projects):
        links = item.get("links", {}) or {}
        statement = insert(Project).values(
            name=item.get("name"),
            tagline=item.get("tagline"),
            problem=item.get("problem"),
            solution=item.get("solution"),
            learning=item.get("learning"),
            tech_stack=json.dumps(item.get("tech_stack", []), ensure_ascii=False),
            demo_link=links.get("demo"),
            github_link=links.get("github"),
            status=item.get("status"),
            sort_order=index,
            visible=True,
        )
        session.execute(
            statement.on_conflict_do_update(
                index_elements=[Project.name],
                set_={
                    column: statement.excluded[column]
                    for column in _PROJECT_FILE_COLUMNS
                },
            )
        )

    return len(projects)


def _seed_skills(session: Session, base: Path) -> tuple[int, int]:
    path = _require(base / "skills.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    category_count = 0
    skill_count = 0

    for cat_index, (category, names) in enumerate(data.items()):
        category_insert = insert(SkillCategory).values(
            name=category, sort_order=cat_index
        )
        session.execute(
            category_insert.on_conflict_do_update(
                index_elements=[SkillCategory.name],
                set_={"sort_order": category_insert.excluded.sort_order},
            )
        )
        category_count += 1
        category_id = session.scalars(
            select(SkillCategory.id).where(SkillCategory.name == category)
        ).one()

        for skill_index, name in enumerate(names):
            skill_insert = insert(Skill).values(
                category_id=category_id, name=name, sort_order=skill_index
            )
            session.execute(
                skill_insert.on_conflict_do_update(
                    index_elements=[Skill.category_id, Skill.name],
                    set_={"sort_order": skill_insert.excluded.sort_order},
                )
            )
            skill_count += 1

    return category_count, skill_count


def run_seed() -> dict[str, int]:
    """Read content files into the database and return processed-entry counts."""
    base = content_dir()
    summary: dict[str, int] = {}

    with get_session() as session:
        summary["about"] = _seed_about(session, base)
        summary["contact"] = _seed_setting_json(
            session, base, "contact.json", "contact"
        )
        summary["impressum"] = _seed_setting_json(
            session, base, "impressum.json", "impressum"
        )
        summary["projects"] = _seed_projects(session, base)
        categories, skills = _seed_skills(session, base)
        summary["skill_categories"] = categories
        summary["skills"] = skills
        session.commit()

    return summary


def main() -> None:
    summary = run_seed()
    for key, value in summary.items():
        print(f"{key}: {value} processed")


if __name__ == "__main__":
    main()
