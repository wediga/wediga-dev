"""Sessions kept on the server.

Every session is a row in ``session``, and each of its parts (a login through
authentik, a login under way, the old admin login and a redeemed recruiter
link) is a row of its own that goes away with it. The accounts from authentik
and the roles a login gets complete them.

Revision ID: 0002_sessions
"""

import sqlalchemy as sa
from alembic import op

from app.db.base import ACCESS_SCHEMA, UUID_DEFAULT

revision = "0002_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

# In the order they are created. They are dropped the other way round.
TABLES = (
    "account",
    "session",
    "role",
    "authentik_login",
    "authentik_login_role",
    "login_flow",
    "legacy_admin_login",
    "recruiter_access",
)


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT)


def _timestamp(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def _reference(name: str, table: str, cascade: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.Uuid,
        sa.ForeignKey(
            f"{ACCESS_SCHEMA}.{table}.id", ondelete="CASCADE" if cascade else None
        ),
        nullable=False,
    )


def _session_reference() -> sa.Column:
    return sa.Column(
        "session_id",
        sa.Uuid,
        sa.ForeignKey(f"{ACCESS_SCHEMA}.session.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )


def upgrade() -> None:
    op.create_table(
        "account",
        _id(),
        sa.Column("authentik_user_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        _timestamp("first_login_at"),
        _timestamp("last_login_at"),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "session",
        _id(),
        sa.Column("token_hash", sa.LargeBinary, nullable=False, unique=True),
        sa.Column("csrf_token", sa.Text, nullable=False),
        sa.Column("user_agent", sa.Text),
        _timestamp("created_at"),
        _timestamp("last_seen_at"),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "role",
        _id(),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "authentik_login",
        _id(),
        _session_reference(),
        _reference("account_id", "account"),
        _timestamp("logged_in_at"),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "authentik_login_role",
        _id(),
        _reference("authentik_login_id", "authentik_login", cascade=True),
        _reference("role_id", "role"),
        sa.UniqueConstraint("authentik_login_id", "role_id"),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "login_flow",
        _id(),
        _session_reference(),
        sa.Column("state", sa.Text, nullable=False),
        sa.Column("nonce", sa.Text, nullable=False),
        sa.Column("verifier", sa.Text, nullable=False),
        sa.Column("target", sa.Text),
        _timestamp("started_at"),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "legacy_admin_login",
        _id(),
        _session_reference(),
        sa.Column("second_factor_done", sa.Boolean, nullable=False),
        schema=ACCESS_SCHEMA,
    )

    op.create_table(
        "recruiter_access",
        _id(),
        _session_reference(),
        _reference("recruiter_link_id", "recruiter_link"),
        _timestamp("redeemed_at"),
        schema=ACCESS_SCHEMA,
    )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table, schema=ACCESS_SCHEMA)
