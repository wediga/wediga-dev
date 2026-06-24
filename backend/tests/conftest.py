"""Shared test fixtures.

Each test session uses an isolated SQLite file via ``WEDIGA_DB_PATH`` so the
real ``data/wediga.db`` is never touched. ``WEDIGA_CONTENT_DIR`` points at the
committed ``content.example`` fixture, so the seed tests never read the
gitignored ``content/``.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    """Isolate the process-level rate limiters between tests.

    The limiters keep per-IP counts in module state, so without a reset the
    repeated logins and redeems across the suite would accumulate and a later
    test could hit a limit by accident.
    """
    from app.auth.ratelimit import login_limiter, redeem_limiter

    login_limiter.clear()
    redeem_limiter.clear()
    yield


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Point the backend at a fresh temporary database file."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("WEDIGA_DB_PATH", str(db_file))
    monkeypatch.setenv("WEDIGA_CONTENT_DIR", str(REPO_ROOT / "content.example"))
    return db_file


@pytest.fixture()
def migrated_db(temp_db):
    """Run migrations against the temporary database."""
    from app.db.migrate import run_migrations

    run_migrations()
    return temp_db


@pytest.fixture()
def seeded_db(migrated_db):
    """Migrate and seed the temporary database."""
    from app.db.seed import run_seed

    run_seed()
    return migrated_db
