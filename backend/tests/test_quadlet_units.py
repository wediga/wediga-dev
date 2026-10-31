"""The production units must reach PostgreSQL and no longer the SQLite volume."""

from pathlib import Path

import pytest

QUADLET_DIR = Path(__file__).resolve().parents[2] / "deploy/quadlet"
DB_ENV_FILE = "EnvironmentFile=/home/web/wediga-dev/wediga-db.env"
DB_SERVICE = "wediga-db.service"
BACKEND_UNITS = ["backend.container", "backend-migrate.container"]


def unit_lines(name: str) -> list[str]:
    return (QUADLET_DIR / name).read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("name", BACKEND_UNITS)
def test_unit_reaches_the_database(name: str) -> None:
    lines = unit_lines(name)

    assert DB_ENV_FILE in lines
    assert "Network=wediga.network" in lines
    assert not any("wediga-data" in line or "WEDIGA_DB_PATH" in line for line in lines)


def test_migration_runs_alembic_after_the_database() -> None:
    lines = unit_lines("backend-migrate.container")

    assert "Exec=alembic upgrade head" in lines
    assert f"Requires={DB_SERVICE}" in lines
    assert f"After={DB_SERVICE}" in lines


def test_database_counts_as_started_only_when_healthy() -> None:
    assert "Notify=healthy" in unit_lines("wediga-db.container")
