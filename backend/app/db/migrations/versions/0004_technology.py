"""Technologies as the single source of skill names.

Each skill becomes a technology, whose topic is the name in lowercase with
every run of other characters turned into one hyphen, and the skill keeps only
a reference to it. A name in two categories, or two names with the same topic,
stop the migration on the unique topic instead of dropping one of them.

Revision ID: 0004_technology
"""

import sqlalchemy as sa
from alembic import op

from app.db.base import SITE_SCHEMA, UUID_DEFAULT

revision = "0004_technology"
down_revision = "0003_profile"
branch_labels = None
depends_on = None

SKILL = f"{SITE_SCHEMA}.skill"
TECHNOLOGY = f"{SITE_SCHEMA}.technology"


def upgrade() -> None:
    op.create_table(
        "technology",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("topic", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        schema=SITE_SCHEMA,
    )
    op.add_column(
        "skill",
        sa.Column(
            "technology_id",
            sa.Uuid,
            sa.ForeignKey(f"{TECHNOLOGY}.id", ondelete="CASCADE"),
            unique=True,
        ),
        schema=SITE_SCHEMA,
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(f"""
            INSERT INTO {TECHNOLOGY} (topic, name)
            SELECT trim(BOTH '-' FROM regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g')),
                   name
            FROM {SKILL}
        """)
    )
    connection.execute(
        sa.text(f"""
            UPDATE {SKILL} skill SET technology_id = technology.id
            FROM {TECHNOLOGY} technology
            WHERE technology.name = skill.name
        """)
    )

    op.alter_column("skill", "technology_id", nullable=False, schema=SITE_SCHEMA)
    op.drop_constraint("skill_category_id_name_key", "skill", schema=SITE_SCHEMA)
    op.drop_column("skill", "name", schema=SITE_SCHEMA)
    op.alter_column(
        "skill", "category_id", new_column_name="skill_category_id", schema=SITE_SCHEMA
    )


def downgrade() -> None:
    op.alter_column(
        "skill", "skill_category_id", new_column_name="category_id", schema=SITE_SCHEMA
    )
    op.add_column("skill", sa.Column("name", sa.Text), schema=SITE_SCHEMA)
    op.get_bind().execute(
        sa.text(f"""
            UPDATE {SKILL} skill SET name = technology.name
            FROM {TECHNOLOGY} technology
            WHERE technology.id = skill.technology_id
        """)
    )
    op.alter_column("skill", "name", nullable=False, schema=SITE_SCHEMA)
    op.create_unique_constraint(
        "skill_category_id_name_key",
        "skill",
        ["category_id", "name"],
        schema=SITE_SCHEMA,
    )
    op.drop_column("skill", "technology_id", schema=SITE_SCHEMA)
    op.drop_table("technology", schema=SITE_SCHEMA)
