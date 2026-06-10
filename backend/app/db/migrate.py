"""Migration runner for the SQLite backend.

Migrations are plain SQL files under ``migrations/`` named with a sortable
prefix (``0001_initial.sql``). The runner records applied versions in the
``schema_migrations`` table, so it only applies files that have not run yet.
Each file is run with ``executescript``, which is not transactional across
statements (it commits any open transaction first), so a multi-statement
migration is not atomic. The current ``0001_initial.sql`` is made only of
``CREATE TABLE IF NOT EXISTS`` statements, where a re-run heals a partial
apply. A future migration with data DML that needs all-or-nothing semantics
must run its statements one by one inside an explicit transaction instead.
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
