"""The repos from GitHub in the shape of the data model, without curation.

``github_repo`` keeps a repo by its GitHub id, which the old rows do not
carry, so the table is emptied and the next sync fills it again. Its texts and
topics move into their own tables, and every run of the sync gets a row in
``github_sync``. The downgrade restores the old structure, empty as well.

Revision ID: 0005_github_sync
"""

import sqlalchemy as sa
from alembic import op

from app.db.base import SITE_SCHEMA, UUID_DEFAULT

revision = "0005_github_sync"
down_revision = "0004_technology"
branch_labels = None
depends_on = None

GITHUB_REPO = f"{SITE_SCHEMA}.github_repo"


def _old_columns() -> tuple[sa.Column, ...]:
    """The columns of the mirror and the curation that the data model drops."""
    return (
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("language", sa.Text),
        sa.Column("stars", sa.Integer),
        sa.Column("url", sa.Text),
        sa.Column("last_push", sa.DateTime(timezone=True)),
        sa.Column("last_sync", sa.DateTime(timezone=True)),
        sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("description_override", sa.Text),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )


def _new_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("github_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("homepage_url", sa.Text),
        sa.Column("archived", sa.Boolean, nullable=False),
        sa.Column(
            "last_seen_sync_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.github_sync.id"),
            nullable=False,
        ),
    )


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT)


def _repo_reference() -> sa.Column:
    return sa.Column(
        "github_repo_id",
        sa.Uuid,
        sa.ForeignKey(f"{GITHUB_REPO}.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "github_sync",
        _id(),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text),
        schema=SITE_SCHEMA,
    )

    op.execute(f"DELETE FROM {GITHUB_REPO}")

    for column in _old_columns():
        op.drop_column("github_repo", column.name, schema=SITE_SCHEMA)

    for column in _new_columns():
        op.add_column("github_repo", column, schema=SITE_SCHEMA)

    op.create_table(
        "text_field",
        _id(),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "github_repo_text",
        _id(),
        _repo_reference(),
        sa.Column(
            "text_field_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.text_field.id"),
            nullable=False,
        ),
        sa.Column("value", sa.Text, nullable=False),
        sa.UniqueConstraint("github_repo_id", "text_field_id"),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "github_repo_technology",
        _id(),
        _repo_reference(),
        sa.Column(
            "technology_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.technology.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("github_repo_id", "technology_id"),
        schema=SITE_SCHEMA,
    )


def downgrade() -> None:
    for table in ("github_repo_technology", "github_repo_text", "text_field"):
        op.drop_table(table, schema=SITE_SCHEMA)

    op.execute(f"DELETE FROM {GITHUB_REPO}")

    for column in _new_columns():
        op.drop_column("github_repo", column.name, schema=SITE_SCHEMA)

    for column in _old_columns():
        op.add_column("github_repo", column, schema=SITE_SCHEMA)

    op.drop_table("github_sync", schema=SITE_SCHEMA)
