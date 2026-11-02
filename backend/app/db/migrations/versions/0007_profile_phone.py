"""A phone number on the profile, empty when there is none.

An existing profile starts with an empty number. The default only fills that
row and is dropped right after, so the column behaves like the other texts of
the profile.

Revision ID: 0007_profile_phone
"""

import sqlalchemy as sa
from alembic import op

from app.db.base import SITE_SCHEMA

revision = "0007_profile_phone"
down_revision = "0006_portfolio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profile",
        sa.Column("phone", sa.Text, nullable=False, server_default=""),
        schema=SITE_SCHEMA,
    )
    op.alter_column("profile", "phone", server_default=None, schema=SITE_SCHEMA)


def downgrade() -> None:
    op.drop_column("profile", "phone", schema=SITE_SCHEMA)
