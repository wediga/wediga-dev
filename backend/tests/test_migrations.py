"""Tests for the migration runner."""

from app.db.migrate import list_tables, run_migrations

EXPECTED_TABLES = {
    "admin",
    "github_repo",
    "link_view",
    "project",
    "recruiter_link",
    "schema_migrations",
    "site_setting",
    "skill",
    "skill_category",
}


def test_migrations_create_all_tables(temp_db) -> None:
    run_migrations()
    assert set(list_tables()) == EXPECTED_TABLES


def test_migrations_are_idempotent(temp_db) -> None:
    first = run_migrations()
    assert first["applied"] == ["0001_initial", "0002_admin_totp"]
    assert first["skipped"] == []

    second = run_migrations()
    assert second["applied"] == []
    assert second["skipped"] == ["0001_initial", "0002_admin_totp"]
    assert set(list_tables()) == EXPECTED_TABLES
