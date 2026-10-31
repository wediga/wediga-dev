"""Shared test fixtures.

The tests run against a real PostgreSQL: locally the container from the
README, in the CI a service of the job. Its schema is rebuilt once per test
run with the Alembic migrations, and every test that uses the database starts
from empty tables. ``WEDIGA_CONTENT_DIR`` points at the committed
``content.example`` fixture, so the seed tests never read the gitignored
``content/``.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# The test database is the PostgreSQL image with its own default user and
# database, and it trusts every connection, so the password is never checked.
# 127.0.0.1 rather than localhost, which hangs on Windows on the IPv6 address.
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_DB", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "not-checked")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")


def alembic_config() -> Config:
    return Config(BACKEND_DIR / "alembic.ini")


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    """Isolate the process-level rate limiters between tests.

    The limiters keep per-IP counts in module state, so without a reset the
    repeated logins and redeems across the suite would accumulate and a later
    test could hit a limit by accident.
    """
    from app.auth.ratelimit import login_limiter, redeem_limiter, totp_limiter

    login_limiter.clear()
    redeem_limiter.clear()
    totp_limiter.clear()
    yield


@pytest.fixture(scope="session")
def _schema() -> None:
    """Drop whatever a previous run left and migrate to the newest revision."""
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")


@pytest.fixture()
def unmigrated_db(_schema):
    """Remove the schema for this test and migrate it again afterwards."""
    command.downgrade(alembic_config(), "base")
    yield
    command.upgrade(alembic_config(), "head")


@pytest.fixture()
def migrated_db(_schema, monkeypatch) -> None:
    """Empty every table of the migrated schema for this test."""
    from app.db.base import ACCESS_SCHEMA, SITE_SCHEMA
    from app.db.connection import get_session

    monkeypatch.setenv("WEDIGA_CONTENT_DIR", str(REPO_ROOT / "content.example"))

    with get_session() as session:
        tables = session.scalars(
            text(
                "SELECT quote_ident(schemaname) || '.' || quote_ident(tablename) "
                "FROM pg_tables WHERE schemaname IN (:access, :site)"
            ),
            {"access": ACCESS_SCHEMA, "site": SITE_SCHEMA},
        ).all()
        session.execute(text(f"TRUNCATE {', '.join(tables)}"))
        session.commit()


@pytest.fixture()
def seeded_db(migrated_db) -> None:
    """Empty the tables and seed them from the example content."""
    from app.db.seed import run_seed

    run_seed()
