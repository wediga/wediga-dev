"""The declarative base that every model of every area derives from.

The schema itself still comes from the SQL files under ``migrations/``, so the
models only describe it and never create it. Timestamps stay ISO 8601 text and
JSON stays text, exactly as the migrations store them. The 0/1 flag columns map
to ``bool``, which SQLite stores as the same 0 and 1.

The models are dataclasses, so their constructors take keyword arguments that
the type checker knows. An id is assigned by SQLite and never passed in, and a
default in a model repeats the default of its column in the schema.
"""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    def as_dict(self) -> dict:
        """Return every column of the row by name, like ``dict(row)`` did."""
        return {
            column.key: getattr(self, column.key) for column in self.__table__.columns
        }
