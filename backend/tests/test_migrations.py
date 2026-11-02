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
        "technology",
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


def _back_to(revision: str):
    """Go back to a revision for one test and to the newest revision after."""
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), revision)
    yield
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")


@pytest.fixture()
def settings_db(_schema):
    yield from _back_to(BEFORE_PROFILE)


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


# The revision before the technologies, with skills that carry their own name.
BEFORE_TECHNOLOGY = "0003_profile"


@pytest.fixture()
def skills_db(_schema):
    yield from _back_to(BEFORE_TECHNOLOGY)


def _insert_skills(skills: dict[str, list[str]]) -> None:
    with get_session() as session:
        for category_order, (category, names) in enumerate(skills.items()):
            category_id = session.execute(
                text(
                    f"INSERT INTO {SITE_SCHEMA}.skill_category (name, sort_order) "
                    "VALUES (:name, :sort_order) RETURNING id"
                ),
                {"name": category, "sort_order": category_order},
            ).scalar_one()
            session.execute(
                text(
                    f"INSERT INTO {SITE_SCHEMA}.skill (category_id, name, sort_order) "
                    "VALUES (:category_id, :name, :sort_order)"
                ),
                [
                    {"category_id": category_id, "name": name, "sort_order": order}
                    for order, name in enumerate(names)
                ],
            )

        session.commit()


def test_technologies_take_over_the_skills(skills_db) -> None:
    skills = {"Web": ["Tailwind CSS", "HTML5"], "Tools": ["n8n", "Scikit-learn"]}
    _insert_skills(skills)

    command.upgrade(alembic_config(), "head")
    categories = repository.list_skill_categories()
    topics = {
        technology["name"]: technology["topic"]
        for technology in repository.list_technologies()
    }

    assert {
        category["name"]: [skill["name"] for skill in category["skills"]]
        for category in categories
    } == skills
    assert topics == {
        "Tailwind CSS": "tailwind-css",
        "HTML5": "html5",
        "n8n": "n8n",
        "Scikit-learn": "scikit-learn",
    }


@pytest.mark.parametrize(
    "skills",
    [
        {"Web": ["Python"], "Languages": ["Python"]},
        {"Web": ["Tailwind CSS", "tailwind css"]},
    ],
    ids=["name-in-two-categories", "same-topic"],
)
def test_clashing_topics_stop_the_migration(skills_db, skills) -> None:
    _insert_skills(skills)

    with pytest.raises(IntegrityError):
        command.upgrade(alembic_config(), "head")
