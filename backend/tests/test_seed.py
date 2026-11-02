"""Tests for the idempotent content seed."""

from sqlalchemy import func, select

from app.content.models import (
    PostalAddress,
    Profile,
    ProfileLink,
    Skill,
    SkillCategory,
    Technology,
)
from app.db.connection import get_session
from app.db.seed import run_seed


def _counts() -> dict[str, int]:
    statements = {
        "categories": select(func.count()).select_from(SkillCategory),
        "skills": select(func.count()).select_from(Skill),
        "technologies": select(func.count()).select_from(Technology),
        "profiles": select(func.count()).select_from(Profile),
        "links": select(func.count()).select_from(ProfileLink),
        "addresses": select(func.count()).select_from(PostalAddress),
    }

    with get_session() as session:
        return {
            name: session.execute(statement).scalar_one()
            for name, statement in statements.items()
        }


def test_seed_loads_content(migrated_db) -> None:
    run_seed()
    counts = _counts()
    assert counts["categories"] == 2
    assert counts["profiles"] == 1
    assert counts["links"] == 2
    assert counts["addresses"] == 1
    assert counts["skills"] == 3
    assert counts["technologies"] == 3


def test_seed_is_idempotent(migrated_db) -> None:
    run_seed()
    first = _counts()
    run_seed()
    second = _counts()
    assert first == second
