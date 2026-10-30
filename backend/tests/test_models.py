"""The models must describe exactly the schema the SQL migrations create."""

from importlib import import_module

from sqlalchemy import inspect

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


def _columns_of_models() -> dict[str, dict[str, bool | None]]:
    for module in MODEL_MODULES:
        import_module(module)

    return {
        table.name: {column.name: column.nullable for column in table.columns}
        for table in Base.metadata.tables.values()
    }


def _columns_of_database() -> dict[str, dict[str, bool | None]]:
    with get_session() as session:
        inspector = inspect(session.connection())
        tables = set(inspector.get_table_names()) - {"schema_migrations"}
        result = {}

        for name in tables:
            primary_key = inspector.get_pk_constraint(name)["constrained_columns"]
            # SQLite reports a primary key column as nullable unless it is
            # declared NOT NULL, while it never holds NULL.
            result[name] = {
                column["name"]: column["nullable"] and column["name"] not in primary_key
                for column in inspector.get_columns(name)
            }

    return result


def test_models_match_migrated_schema(migrated_db) -> None:
    assert _columns_of_models() == _columns_of_database()
