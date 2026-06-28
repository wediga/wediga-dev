"""Migration runner for the SQLite backend.

Migrations are SQL files under ``migrations/`` with a sortable prefix
(``0001_initial.sql``). The runner records applied versions in
``schema_migrations`` and applies only the pending files, each via one
``executescript``. ``executescript`` commits any open transaction first, so a
multi-statement file is not atomic; ``0001_initial.sql`` is all
``CREATE TABLE IF NOT EXISTS``, where a re-run heals a partial apply.
"""

from pathlib import Path

from app.db.connection import get_connection, now

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _applied_versions(conn) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def run_migrations() -> dict[str, list[str]]:
    """Apply pending migrations and return applied and skipped versions."""
    applied: list[str] = []
    skipped: list[str] = []

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with get_connection() as conn:
        done = _applied_versions(conn)
        for path in files:
            version = path.stem
            if version in done:
                skipped.append(version)
                continue
            sql = path.read_text(encoding="utf-8")
            try:
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) "
                    "VALUES (?, ?)",
                    (version, now()),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            applied.append(version)

    return {"applied": applied, "skipped": skipped}


def list_tables() -> list[str]:
    """Return the user tables present in the database."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


def main() -> None:
    result = run_migrations()
    for version in result["applied"]:
        print(f"applied {version}")
    for version in result["skipped"]:
        print(f"skipped {version}")
    print("tables: " + ", ".join(list_tables()))


if __name__ == "__main__":
    main()
