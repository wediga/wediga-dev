"""The portfolio from the synced repos, in place of the project table.

A project becomes the entry of the repo its GitHub link points to, matched by
the last part of the link and the repo name from the sync. Its texts become
own texts of the entry, the tagline as the description, and its status, order
and visibility carry over. A project without a synced repo is dropped, and a
status without a match stops the migration instead of guessing one. The
downgrade restores the project table, empty.

Revision ID: 0006_portfolio
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import SITE_SCHEMA, UUID_DEFAULT

revision = "0006_portfolio"
down_revision = "0005_github_sync"
branch_labels = None
depends_on = None

PROJECT = f"{SITE_SCHEMA}.project"
TEXT_FIELD = f"{SITE_SCHEMA}.text_field"

# The statuses in their order, as key and label.
STATUSES = (
    ("done", "Fertig"),
    ("wip", "In Entwicklung"),
    ("early", "Frühe Entwicklung"),
    ("stopped", "Eingestellt"),
)

# Which column of a project becomes the own text of which field.
TEXTS = {
    "name": "name",
    "tagline": "description",
    "problem": "problem",
    "solution": "solution",
    "learning": "learning",
}

# Every project with the repo its GitHub link points to.
MATCHED_PROJECTS = f"""
    SELECT p.*, t.github_repo_id
    FROM {PROJECT} p
    JOIN {SITE_SCHEMA}.github_repo_text t
        ON lower(t.value) = lower(regexp_replace(rtrim(p.github_link, '/'), '^.*/', ''))
    JOIN {TEXT_FIELD} f ON f.id = t.text_field_id AND f.key = 'name'
"""


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True, server_default=UUID_DEFAULT)


def _sort_order() -> sa.Column:
    return sa.Column("sort_order", sa.Integer, nullable=False, server_default="0")


def _create_tables() -> tuple[sa.Table, sa.Table, sa.Table]:
    status = op.create_table(
        "project_status",
        _id(),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        schema=SITE_SCHEMA,
    )
    entry = op.create_table(
        "portfolio_entry",
        _id(),
        sa.Column(
            "github_repo_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.github_repo.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "project_status_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.project_status.id"),
            nullable=False,
        ),
        _sort_order(),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        schema=SITE_SCHEMA,
    )
    override = op.create_table(
        "portfolio_text_override",
        _id(),
        sa.Column(
            "portfolio_entry_id",
            sa.Uuid,
            sa.ForeignKey(f"{SITE_SCHEMA}.portfolio_entry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "text_field_id",
            sa.Uuid,
            sa.ForeignKey(f"{TEXT_FIELD}.id"),
            nullable=False,
        ),
        sa.Column("value", sa.Text, nullable=False),
        sa.UniqueConstraint("portfolio_entry_id", "text_field_id"),
        schema=SITE_SCHEMA,
    )

    return status, entry, override


def _take_over_projects(status: sa.Table, entry: sa.Table, override: sa.Table) -> None:
    bind = op.get_bind()
    status_ids = {
        label: status_id
        for status_id, label in bind.execute(
            sa.insert(status)
            .values(
                [
                    {"key": key, "label": label, "sort_order": order}
                    for order, (key, label) in enumerate(STATUSES)
                ]
            )
            .returning(status.c.id, status.c.label)
        )
    }
    # The sync adds a text field the first time it needs it, so a field no
    # repo has a text for may still be missing.
    bind.execute(
        sa.text(
            f"INSERT INTO {TEXT_FIELD} (key) SELECT unnest(CAST(:keys AS text[])) "
            "ON CONFLICT (key) DO NOTHING"
        ),
        {"keys": list(TEXTS.values())},
    )
    field_ids = dict(bind.execute(sa.text(f"SELECT key, id FROM {TEXT_FIELD}")).all())

    for project in bind.execute(sa.text(MATCHED_PROJECTS)).mappings():
        if project["status"] not in status_ids:
            raise ValueError(f"project status without a match: {project['status']!r}")

        entry_id = bind.execute(
            sa.insert(entry)
            .values(
                github_repo_id=project["github_repo_id"],
                project_status_id=status_ids[project["status"]],
                sort_order=project["sort_order"],
                published_at=sa.func.now() if project["visible"] else None,
            )
            .returning(entry.c.id)
        ).scalar_one()
        texts = [
            {
                "portfolio_entry_id": entry_id,
                "text_field_id": field_ids[key],
                "value": project[column],
            }
            for column, key in TEXTS.items()
            if project[column] and project[column].strip()
        ]

        if texts:
            bind.execute(sa.insert(override), texts)


def upgrade() -> None:
    _take_over_projects(*_create_tables())
    op.drop_table("project", schema=SITE_SCHEMA)


def downgrade() -> None:
    for table in ("portfolio_text_override", "portfolio_entry", "project_status"):
        op.drop_table(table, schema=SITE_SCHEMA)

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
