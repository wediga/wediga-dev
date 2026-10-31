"""Tests for the Alembic migrations."""

from sqlalchemy import inspect

from app.db.base import ACCESS_SCHEMA, SITE_SCHEMA
from app.db.connection import get_session

EXPECTED_TABLES = {
    ACCESS_SCHEMA: {"admin", "link_view", "recruiter_link"},
    SITE_SCHEMA: {
        "cv_document",
        "github_repo",
        "project",
        "site_setting",
        "skill",
        "skill_category",
    },
}


def _schemas() -> set[str]:
    with get_session() as session:
        return set(inspect(session.connection()).get_schema_names())


def test_upgrade_creates_every_table(_schema) -> None:
    with get_session() as session:
        inspector = inspect(session.connection())
        tables = {
            schema: set(inspector.get_table_names(schema=schema))
            for schema in EXPECTED_TABLES
        }

    assert tables == EXPECTED_TABLES


def test_downgrade_removes_both_schemas(unmigrated_db) -> None:
    assert _schemas().isdisjoint(EXPECTED_TABLES)
