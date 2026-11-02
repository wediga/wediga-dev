"""Tests for the Alembic migrations."""

import json

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.content import repository
from app.db.base import ACCESS_SCHEMA, SITE_SCHEMA
from app.db.connection import get_session
from app.portfolio import repository as portfolio
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
        "github_repo_technology",
        "github_repo_text",
        "github_sync",
        "link_kind",
        "portfolio_entry",
        "portfolio_text_override",
        "postal_address",
        "profile",
        "profile_link",
        "project_status",
        "skill",
        "skill_category",
        "technology",
        "text_field",
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


# The revision before the sync tables, with a repo in the old shape.
BEFORE_GITHUB_SYNC = "0004_technology"


@pytest.fixture()
def old_repo_db(_schema):
    yield from _back_to(BEFORE_GITHUB_SYNC)


def test_old_repos_are_removed_for_the_next_sync(old_repo_db) -> None:
    with get_session() as session:
        session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.github_repo (name, pinned) "
                "VALUES ('alpha', true)"
            )
        )
        session.commit()

    command.upgrade(alembic_config(), "head")

    with get_session() as session:
        repos = session.scalar(text(f"SELECT count(*) FROM {SITE_SCHEMA}.github_repo"))

    assert repos == 0


# The revision before the portfolio, with projects in the old table.
BEFORE_PORTFOLIO = "0005_github_sync"


@pytest.fixture()
def projects_db(_schema):
    yield from _back_to(BEFORE_PORTFOLIO)


def _insert_synced_repo(name: str) -> None:
    """Write a repo as the sync of revision 0005 left it, with only its name."""
    with get_session() as session:
        run_id = session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.github_sync (started_at, finished_at) "
                "VALUES (now(), now()) RETURNING id"
            )
        ).scalar_one()
        repo_id = session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.github_repo "
                "(github_id, archived, last_seen_sync_id) "
                "VALUES (1, false, :run_id) RETURNING id"
            ),
            {"run_id": run_id},
        ).scalar_one()
        field_id = session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.text_field (key) "
                "VALUES ('name') RETURNING id"
            )
        ).scalar_one()
        session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.github_repo_text "
                "(github_repo_id, text_field_id, value) VALUES (:repo, :field, :name)"
            ),
            {"repo": repo_id, "field": field_id, "name": name},
        )
        session.commit()


def _insert_projects(*projects: dict) -> None:
    with get_session() as session:
        session.execute(
            text(
                f"INSERT INTO {SITE_SCHEMA}.project "
                "(name, tagline, problem, github_link, status, sort_order, visible) "
                "VALUES (:name, :tagline, :problem, :github_link, :status, "
                ":sort_order, :visible)"
            ),
            [
                {
                    "tagline": None,
                    "problem": None,
                    "sort_order": 0,
                    "visible": True,
                    **project,
                }
                for project in projects
            ],
        )
        session.commit()


def test_projects_become_entries_of_their_repos(projects_db) -> None:
    _insert_synced_repo("monster-cr-predictor")
    _insert_projects(
        {
            "name": "Monster CR Predictor",
            "tagline": "CR vorhersagen",
            "problem": "Zu grob",
            "github_link": "https://github.com/wediga/Monster-CR-Predictor/",
            "status": "Fertig",
            "sort_order": 3,
        },
        {
            "name": "Arcanalyse",
            "github_link": "https://github.com/wediga/Arcanalyse",
            "status": "Frühe Entwicklung",
        },
    )

    command.upgrade(alembic_config(), "head")
    [tile] = portfolio.tiles()
    [repo] = portfolio.admin_overview()["repos"]

    assert tile["texts"] == {
        "name": "Monster CR Predictor",
        "description": "CR vorhersagen",
        "problem": "Zu grob",
    }
    assert tile["status"]["label"] == "Fertig"
    assert repo["entry"]["sort_order"] == 3


def test_hidden_project_becomes_an_unpublished_entry(projects_db) -> None:
    _insert_synced_repo("alpha")
    _insert_projects(
        {
            "name": "Alpha",
            "github_link": "https://github.com/wediga/alpha",
            "status": "In Entwicklung",
            "visible": False,
        }
    )

    command.upgrade(alembic_config(), "head")
    [repo] = portfolio.admin_overview()["repos"]

    assert portfolio.tiles() == []
    assert repo["entry"]["published"] is False
    assert repo["entry"]["texts"] == {"name": "Alpha"}


def test_status_without_a_match_stops_the_migration(projects_db) -> None:
    _insert_synced_repo("alpha")
    _insert_projects(
        {
            "name": "Alpha",
            "github_link": "https://github.com/wediga/alpha",
            "status": "Irgendwas",
        }
    )

    with pytest.raises(ValueError, match="Irgendwas"):
        command.upgrade(alembic_config(), "head")
