"""The declarative base that every model of every area derives from.

The schema comes from the Alembic migrations under ``migrations/``, so the
models only describe it and never create it. ``tests/test_models.py`` checks
that both agree. Every timestamp is a ``timestamptz``.

The models are dataclasses, so their constructors take keyword arguments that
the type checker knows. An id is assigned by PostgreSQL and never passed in,
and a default in a model repeats the default of its column in the schema.
"""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, Text, text
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

ACCESS_SCHEMA = "access"
SITE_SCHEMA = "site"


# The default of every ``id`` column, a UUIDv7 that PostgreSQL creates.
UUID_DEFAULT = text("uuidv7()")


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    type_annotation_map: ClassVar[dict] = {
        str: Text,
        datetime: DateTime(timezone=True),
    }

    def as_dict(self) -> dict:
        """Return every column of the row by name, like ``dict(row)`` did."""
        return {
            column.key: getattr(self, column.key) for column in self.__table__.columns
        }
