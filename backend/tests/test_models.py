"""The models must describe exactly the schema the migrations create: the same
tables, columns, types, NULL rules, keys and defaults."""

from importlib import import_module

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Column, DefaultClause, inspect
from sqlalchemy.sql.schema import ScalarElementColumnDefault

from app.db.base import ACCESS_SCHEMA, SITE_SCHEMA, Base
from app.db.connection import get_session

# Each area keeps its models in its own module, and a model only reaches
# ``Base.metadata`` once its module is imported.
MODEL_MODULES = (
    "app.auth.models",
    "app.content.models",
    "app.github.models",
    "app.recruiter.models",
)


@pytest.fixture(scope="module", autouse=True)
def _all_models() -> None:
    for module in MODEL_MODULES:
        import_module(module)


def _include_schema(name, type_, *_) -> bool:
    # Alembic's own bookkeeping table lives outside the app's schemas.
    return type_ != "table" or name != "alembic_version"


def test_models_match_migrated_schema(_schema) -> None:
    with get_session() as session:
        context = MigrationContext.configure(
            session.connection(),
            opts={
                "include_schemas": True,
                "include_name": lambda name, type_, parent: (
                    type_ != "schema" or name in (ACCESS_SCHEMA, SITE_SCHEMA)
                ),
                "include_object": _include_schema,
                "compare_type": True,
            },
        )

        assert compare_metadata(context, Base.metadata) == []


def _python_default(column: Column) -> str | None:
    if not isinstance(column.default, ScalarElementColumnDefault):
        return None

    value = column.default.arg

    if value is None:
        return None

    # PostgreSQL reports a boolean default as true or false.
    return str(value).lower() if isinstance(value, bool) else str(value)


def test_model_defaults_match_column_defaults(_schema) -> None:
    with get_session() as session:
        inspector = inspect(session.connection())

        for table in Base.metadata.tables.values():
            database = {
                column["name"]: column["default"]
                for column in inspector.get_columns(table.name, schema=table.schema)
            }

            for column in table.columns:
                expected = (
                    str(column.server_default.arg)
                    if isinstance(column.server_default, DefaultClause)
                    else _python_default(column)
                )

                assert database[column.name] == expected, f"{table}.{column.name}"
