"""Tests for the idempotent content seed."""

from sqlalchemy import func, select

from app.content.models import Project, SiteSetting, Skill, SkillCategory
from app.db.connection import get_session
from app.db.seed import run_seed


def _counts() -> dict[str, int]:
    statements = {
        "projects": select(func.count()).select_from(Project),
        "categories": select(func.count()).select_from(SkillCategory),
        "skills": select(func.count()).select_from(Skill),
        "about": select(func.count()).where(SiteSetting.key == "about_text"),
    }

    with get_session() as session:
        return {
            name: session.execute(statement).scalar_one()
            for name, statement in statements.items()
        }


def test_seed_loads_content(migrated_db) -> None:
    run_seed()
    counts = _counts()
    assert counts["projects"] == 1
    assert counts["categories"] == 2
    assert counts["about"] == 1
    assert counts["skills"] > 0


def test_seed_is_idempotent(migrated_db) -> None:
    run_seed()
    first = _counts()
    run_seed()
    second = _counts()
    assert first == second
