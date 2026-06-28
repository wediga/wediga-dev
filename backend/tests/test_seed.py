"""Tests for the idempotent content seed."""

from app.db.connection import get_connection
from app.db.seed import run_seed


def _counts() -> dict[str, int]:
    with get_connection() as conn:
        projects = conn.execute("SELECT COUNT(*) FROM project").fetchone()[0]
        categories = conn.execute(
            "SELECT COUNT(*) FROM skill_category"
        ).fetchone()[0]
        skills = conn.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
        about = conn.execute(
            "SELECT COUNT(*) FROM site_setting WHERE key = 'about_text'"
        ).fetchone()[0]
    return {
        "projects": projects,
        "categories": categories,
        "skills": skills,
        "about": about,
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
