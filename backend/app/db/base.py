"""The declarative base that every model of every area derives from.

The schema itself still comes from the SQL files under ``migrations/``, so the
models only describe it and never create it. Timestamps stay ISO 8601 text and
JSON stays text, exactly as the migrations store them. The 0/1 flag columns map
to ``bool``, which SQLite stores as the same 0 and 1.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
