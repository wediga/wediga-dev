"""The models of each area must describe exactly the tables the SQL migrations
create for it, down to which columns may be NULL and their defaults."""

from importlib import import_module

import pytest
from sqlalchemy import Column, inspect
from sqlalchemy.sql.schema import ScalarElementColumnDefault

from app.db.base import Base
from app.db.connection import get_session

# Each area keeps its models in its own module, and a model only reaches
# ``Base.metadata`` once its module is imported.
MODEL_MODULES = (
    "app.auth.models",
    "app.content.models",
    "app.github.models",
    "app.recruiter.models",
)

# A column as both sides describe it: may it hold NULL, and its default as the
# SQL text of the schema.
ColumnShape = tuple[bool | None, str | None]


def _tables_of_area(module: str) -> set[str]:
    import_module(module)

    return {
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if mapper.class_.__module__ == module
    }


def _model_default(column: Column) -> str | None:
    if not isinstance(column.default, ScalarElementColumnDefault):
        return None

    value = column.default.arg

    if value is None:
        return None

    # The schema writes a boolean default as 0 or 1.
    return str(int(value)) if isinstance(value, bool) else str(value)


def _columns_of_models(tables: set[str]) -> dict[str, dict[str, ColumnShape]]:
    return {
        name: {
            column.name: (column.nullable, _model_default(column))
            for column in Base.metadata.tables[name].columns
        }
        for name in tables
    }


def _columns_of_database(tables: set[str]) -> dict[str, dict[str, ColumnShape]]:
    with get_session() as session:
        inspector = inspect(session.connection())
        result = {}

        for name in tables:
            primary_key = inspector.get_pk_constraint(name)["constrained_columns"]
            # SQLite reports a primary key column as nullable unless it is
            # declared NOT NULL, while it never holds NULL.
            result[name] = {
                column["name"]: (
                    column["nullable"] and column["name"] not in primary_key,
                    column["default"],
                )
                for column in inspector.get_columns(name)
            }

    return result


@pytest.mark.parametrize(
    "module", MODEL_MODULES, ids=[module.split(".")[1] for module in MODEL_MODULES]
)
def test_models_of_area_match_migrated_schema(migrated_db, module: str) -> None:
    tables = _tables_of_area(module)

    assert tables
    assert _columns_of_models(tables) == _columns_of_database(tables)


def test_every_table_belongs_to_an_area(migrated_db) -> None:
    with get_session() as session:
        tables = set(inspect(session.connection()).get_table_names())

    areas = set().union(*(_tables_of_area(module) for module in MODEL_MODULES))

    assert areas == tables - {"schema_migrations"}
