"""The first schema on PostgreSQL.

The recruiter links, their views and the admin row get their final form from
the data model in the plan. Projects, skills, the GitHub repos and
the key-value settings move over in the shape they had in SQLite, only with
UUIDs, timestamptz, boolean and jsonb.

Revision ID: 0001_initial
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import ACCESS_SCHEMA, SITE_SCHEMA, UUID_DEFAULT

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT)


def _timestamp(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _sort_order() -> sa.Column:
    return sa.Column("sort_order", sa.Integer, nullable=False, server_default="0")


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA {ACCESS_SCHEMA}")
    op.execute(f"CREATE SCHEMA {SITE_SCHEMA}")

    op.create_table(
        "admin",
        _id(),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("totp_secret", sa.Text),
        sa.Column(
            "totp_enabled", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        schema=ACCESS_SCHEMA,
    )
    # A unique index on a constant allows at most one row.
    op.create_index(
        "admin_single_row",
        "admin",
        [sa.text("(true)")],
        unique=True,
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "recruiter_link",
        _id(),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("label", sa.Text),
        _timestamp("created_at"),
        _timestamp("expires_at", nullable=True),
        _timestamp("revoked_at", nullable=True),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "link_view",
        _id(),
        sa.Column(
            "recruiter_link_id",
            sa.Uuid,
            sa.ForeignKey(f"{ACCESS_SCHEMA}.recruiter_link.id"),
            nullable=False,
        ),
        _timestamp("viewed_at"),
        sa.Column("origin", sa.Text, nullable=False),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "project",
        _id(),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("tagline", sa.Text),
        sa.Column("problem", sa.Text),
        sa.Column("solution", sa.Text),
        sa.Column("learning", sa.Text),
        sa.Column("tech_stack", JSONB),
        sa.Column("demo_link", sa.Text),
        sa.Column("github_link", sa.Text),
        sa.Column("status", sa.Text),
        _sort_order(),
        sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.true()),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "skill_category",
        _id(),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        _sort_order(),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "skill",
        _id(),
        sa.Column(
            "category_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.skill_category.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        _sort_order(),
        sa.UniqueConstraint("category_id", "name"),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "github_repo",
        _id(),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("language", sa.Text),
        sa.Column("stars", sa.Integer),
        sa.Column("url", sa.Text),
        _timestamp("last_push", nullable=True),
        _timestamp("last_sync", nullable=True),
        sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("description_override", sa.Text),
        _sort_order(),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "site_setting",
        _id(),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        sa.Column("value", JSONB, nullable=False),
        _timestamp("updated_at"),
        schema=SITE_SCHEMA,
    )


def downgrade() -> None:
    op.execute(f"DROP SCHEMA {SITE_SCHEMA} CASCADE")
    op.execute(f"DROP SCHEMA {ACCESS_SCHEMA} CASCADE")
