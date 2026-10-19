"""One SQLite connection helper over the stdlib ``sqlite3`` driver, shared by
the migration runner, seed, bootstrap and routes."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from app.paths import db_path


def now() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(str(db_path()))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()
