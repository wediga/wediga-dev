"""Alembic environment: runs the migrations over the backend's own engine.

The migrations are written by hand, so no metadata is handed to Alembic.
"""

from logging.config import fileConfig

from alembic import context

from app.db.connection import engine

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)

with engine().connect() as connection:
    context.configure(connection=connection)

    with context.begin_transaction():
        context.run_migrations()
