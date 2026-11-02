"""The portrait in the database instead of a file in the frontend.

The table holds at most one row. It starts empty, the portrait is uploaded in
the admin area after the deploy.

Revision ID: 0008_portrait
"""

import sqlalchemy as sa
from alembic import op

from app.db.base import SITE_SCHEMA, UUID_DEFAULT

revision = "0008_portrait"
down_revision = "0007_profile_phone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portrait",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("content", sa.LargeBinary, nullable=False),
        sa.Column("focus_x", sa.Integer, nullable=False),
        sa.Column("focus_y", sa.Integer, nullable=False),
        sa.Column("zoom", sa.Integer, nullable=False),
        schema=SITE_SCHEMA,
    )
    # A unique index on a constant allows at most one row.
    op.create_index(
        "portrait_single_row",
        "portrait",
        [sa.text("(true)")],
        unique=True,
        schema=SITE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("portrait", schema=SITE_SCHEMA)
