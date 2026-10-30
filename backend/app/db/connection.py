"""Database access helpers: a SQLAlchemy session for the repositories, seed,
bootstrap and routes, and a raw ``sqlite3`` connection for the migration
runner, which applies the SQL files with ``executescript``."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

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


def _enable_foreign_keys(dbapi_connection: sqlite3.Connection, _record) -> None:
    dbapi_connection.execute("PRAGMA foreign_keys = ON")


@cache
def _engine(path: str) -> Engine:
    """Return one engine per database file, since the tests switch the file.

    ``NullPool`` opens and closes a connection per session like the stdlib
    helper above, so no file handle outlives a request.
    """
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    event.listen(engine, "connect", _enable_foreign_keys)

    return engine


def get_session() -> Session:
    """Return a session on the configured database, used as ``with``."""
    return Session(_engine(str(db_path())))
