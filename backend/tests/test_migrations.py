"""Tests for the Alembic migrations."""

import json

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.content import repository
from app.db.base import ACCESS_SCHEMA, SITE_SCHEMA
from app.db.connection import get_session
from tests.conftest import alembic_config

EXPECTED_TABLES = {
    ACCESS_SCHEMA: {
        "account",
        "admin",
        "authentik_login",
        "authentik_login_role",
        "legacy_admin_login",
        "link_view",
        "login_flow",
        "recruiter_access",
        "recruiter_link",
        "role",
        "session",
    },
    SITE_SCHEMA: {
        "cv_document",
        "github_repo",
        "link_kind",
        "postal_address",
        "profile",
        "profile_link",
        "project",
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


# The revision before the profile, with the settings as they were in production.
BEFORE_PROFILE = "0002_sessions"
CONTACT = {
    "name": "Alexander Wedig",
    "email": "a@example.com",
    "github": "https://github.com/example",
    "linkedin": "https://linkedin.com/in/example",
}


@pytest.fixture()
def settings_db(_schema):
    """Go back to the settings for this test and to the newest revision after."""
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), BEFORE_PROFILE)
    yield
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")


def _insert_settings(settings: dict[str, object]) -> None:
    with get_session() as session:
        session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.site_setting (key, value, updated_at) "
                "VALUES (:key, CAST(:value AS jsonb), now())"
            ),
            [
                {"key": key, "value": json.dumps(value)}
                for key, value in settings.items()
            ],
        )
        session.commit()


def test_profile_takes_over_the_settings(settings_db) -> None:
    impressum = {
        **CONTACT,
        "address": {"street": "Street 1", "city": "12679 Berlin"},
    }
    _insert_settings({"about_text": "# Hi", "contact": CONTACT, "impressum": impressum})

    command.upgrade(alembic_config(), "head")
    profile = repository.get_profile()

    assert profile is not None
    assert profile.model_dump() == {
        "name": CONTACT["name"],
        "email": CONTACT["email"],
        "about_md": "# Hi",
        "links": {"github": CONTACT["github"], "linkedin": CONTACT["linkedin"]},
        "address": {"street": "Street 1", "postal_code": "12679", "city": "Berlin"},
    }


def test_city_without_postal_code_stops_the_migration(settings_db) -> None:
    impressum = {**CONTACT, "address": {"street": "Street 1", "city": "Berlin"}}
    _insert_settings({"contact": CONTACT, "impressum": impressum})

    with pytest.raises(IntegrityError):
        command.upgrade(alembic_config(), "head")
