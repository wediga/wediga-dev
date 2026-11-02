"""Idempotent seed of database content from the content directory.

Reads the content files and upserts them on a stable natural key, so a re-run
makes no duplicates and pulls in file edits, never writing back to the files.
The summary counts entries processed, not rows changed.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.content import repository
from app.content.models import Skill, SkillCategory, Technology
from app.content.schemas import ProfileContent, TechnologyWrite
from app.db.connection import get_session
from app.paths import content_dir


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"content file missing: {path}")
    return path


def _seed_profile(session: Session, base: Path) -> int:
    data = json.loads(_require(base / "profile.json").read_text(encoding="utf-8"))
    about = _require(base / "about.md").read_text(encoding="utf-8")
    repository.save_profile(session, ProfileContent(**data, about_md=about))

    return 1


def _seed_skills(session: Session, base: Path) -> tuple[int, int]:
    path = _require(base / "skills.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    category_count = 0
    skill_count = 0

    for cat_index, (category, entries) in enumerate(data.items()):
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

        for skill_index, entry in enumerate(entries):
            technology = TechnologyWrite.model_validate(entry)
            technology_insert = insert(Technology).values(
                topic=technology.topic, name=technology.name
            )
            technology_id = session.scalars(
                technology_insert.on_conflict_do_update(
                    index_elements=[Technology.topic],
                    set_={"name": technology_insert.excluded.name},
                ).returning(Technology.id)
            ).one()
            skill_insert = insert(Skill).values(
                skill_category_id=category_id,
                technology_id=technology_id,
                sort_order=skill_index,
            )
            session.execute(
                skill_insert.on_conflict_do_update(
                    index_elements=[Skill.technology_id],
                    set_={
                        "skill_category_id": skill_insert.excluded.skill_category_id,
                        "sort_order": skill_insert.excluded.sort_order,
                    },
                )
            )
            skill_count += 1

    return category_count, skill_count


def run_seed() -> dict[str, int]:
    """Read content files into the database and return processed-entry counts."""
    base = content_dir()
    summary: dict[str, int] = {}

    with get_session() as session:
        summary["profile"] = _seed_profile(session, base)
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
