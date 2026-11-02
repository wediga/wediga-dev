"""The profile in place of the key-value settings.

About, contact and impressum move from ``site_setting`` into ``profile``, its
links and its postal address. Name, email and links come from the contact,
which held the same values as the impressum, and the address comes from the
impressum, whose city held postal code and city together. The downgrade only
restores the structure, the way back for the data is the nightly backup.

Revision ID: 0003_profile
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.content.schemas import LINK_KINDS
from app.db.base import SITE_SCHEMA, UUID_DEFAULT

revision = "0003_profile"
down_revision = "0002_sessions"
branch_labels = None
depends_on = None

# In the order they are created. They are dropped the other way round.
TABLES = ("profile", "link_kind", "profile_link", "postal_address")

# A postal code, whitespace and the city, as the impressum held it.
POSTAL_CODE_AND_CITY = r"^(\S+)\s+(.+)$"


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT)


def _text(name: str) -> sa.Column:
    return sa.Column(name, sa.Text, nullable=False)


def _profile_reference(unique: bool = False) -> sa.Column:
    return sa.Column(
        "profile_id",
        sa.Uuid,
        sa.ForeignKey(f"{SITE_SCHEMA}.profile.id", ondelete="CASCADE"),
        nullable=False,
        unique=unique,
    )


def _create_tables() -> None:
    op.create_table(
        "profile",
        _id(),
        _text("name"),
        _text("email"),
        _text("about_md"),
        schema=SITE_SCHEMA,
    )
    # A unique index on a constant allows at most one row.
    op.create_index(
        "profile_single_row",
        "profile",
        [sa.text("(true)")],
        unique=True,
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "link_kind",
        _id(),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "profile_link",
        _id(),
        _profile_reference(),
        sa.Column(
            "link_kind_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.link_kind.id"),
            nullable=False,
        ),
        _text("url"),
        sa.UniqueConstraint("profile_id", "link_kind_id"),
        schema=SITE_SCHEMA,
    )

    op.create_table(
        "postal_address",
        _id(),
        _profile_reference(unique=True),
        _text("street"),
        _text("postal_code"),
        _text("city"),
        schema=SITE_SCHEMA,
    )


def _transfer_settings() -> None:
    settings = f"{SITE_SCHEMA}.site_setting"
    connection = op.get_bind()

    connection.execute(
        sa.text(f"""
            INSERT INTO {SITE_SCHEMA}.profile (name, email, about_md)
            SELECT contact.value ->> 'name',
                   contact.value ->> 'email',
                   COALESCE(about.value #>> '{{}}', '')
            FROM {settings} contact
            LEFT JOIN {settings} about ON about.key = 'about_text'
            WHERE contact.key = 'contact'
        """)
    )

    connection.execute(
        sa.text(f"INSERT INTO {SITE_SCHEMA}.link_kind (key) VALUES (:key)"),
        [{"key": kind} for kind in LINK_KINDS],
    )

    connection.execute(
        sa.text(f"""
            INSERT INTO {SITE_SCHEMA}.profile_link (profile_id, link_kind_id, url)
            SELECT profile.id, kind.id, contact.value ->> kind.key
            FROM {SITE_SCHEMA}.profile profile
            CROSS JOIN {SITE_SCHEMA}.link_kind kind
            JOIN {settings} contact ON contact.key = 'contact'
            WHERE COALESCE(contact.value ->> kind.key, '') <> ''
        """)
    )

    # A city without a postal code in front matches nothing, leaves both parts
    # NULL and so stops the migration instead of storing a wrong address.
    connection.execute(
        sa.text(f"""
            INSERT INTO {SITE_SCHEMA}.postal_address
                (profile_id, street, postal_code, city)
            SELECT profile.id,
                   impressum.value #>> '{{address,street}}',
                   parts[1],
                   parts[2]
            FROM {SITE_SCHEMA}.profile profile
            JOIN {settings} impressum ON impressum.key = 'impressum'
            CROSS JOIN LATERAL regexp_match(
                impressum.value #>> '{{address,city}}', :pattern
            ) AS parts
            WHERE jsonb_typeof(impressum.value -> 'address') = 'object'
        """),
        {"pattern": POSTAL_CODE_AND_CITY},
    )


def upgrade() -> None:
    _create_tables()
    _transfer_settings()
    op.drop_table("site_setting", schema=SITE_SCHEMA)


def downgrade() -> None:
    op.create_table(
        "site_setting",
        _id(),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema=SITE_SCHEMA,
    )

    for table in reversed(TABLES):
        op.drop_table(table, schema=SITE_SCHEMA)
