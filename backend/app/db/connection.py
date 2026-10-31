"""Database access helpers: one SQLAlchemy engine on the app's PostgreSQL and a
session for the repositories, seed, bootstrap and routes.

Every part of the connection comes from the environment. In production it is
``wediga-db.env``, the one file the database container reads as well, so user,
database and password are written down only there.
"""

import os
from datetime import UTC, datetime
from functools import cache

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session

USER_VARIABLE = "POSTGRES_USER"
PASSWORD_VARIABLE = "POSTGRES_PASSWORD"
HOST_VARIABLE = "POSTGRES_HOST"
PORT_VARIABLE = "POSTGRES_PORT"
DATABASE_VARIABLE = "POSTGRES_DB"


def now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)


def _required(variable: str) -> str:
    value = os.environ.get(variable)

    if not value:
        raise RuntimeError(f"{variable} must be set to reach the database")

    return value


def _port() -> int:
    raw = _required(PORT_VARIABLE)

    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{PORT_VARIABLE} must be a number") from None


def database_url() -> URL:
    """Return the URL of the app's database, built from the environment."""
    return URL.create(
        "postgresql+psycopg",
        username=_required(USER_VARIABLE),
        password=_required(PASSWORD_VARIABLE),
        host=_required(HOST_VARIABLE),
        port=_port(),
        database=_required(DATABASE_VARIABLE),
    )


@cache
def engine() -> Engine:
    """Return the one engine of the process, created on first use."""
    return create_engine(database_url())


def get_session() -> Session:
    """Return a session on the app's database, used as ``with``."""
    return Session(engine())
