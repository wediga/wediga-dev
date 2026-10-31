"""Models of the site content: projects, skills and the key-value settings.

They keep the shape the tables had in SQLite, as a step towards the data model
in the plan, which replaces them with the profile and the portfolio from
GitHub.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base


class Project(Base):
    __tablename__ = "project"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    name: Mapped[str] = mapped_column(unique=True)
    tagline: Mapped[str | None] = mapped_column(default=None)
    problem: Mapped[str | None] = mapped_column(default=None)
    solution: Mapped[str | None] = mapped_column(default=None)
    learning: Mapped[str | None] = mapped_column(default=None)
    tech_stack: Mapped[list[str] | None] = mapped_column(JSONB, default=None)
    demo_link: Mapped[str | None] = mapped_column(default=None)
    github_link: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    visible: Mapped[bool] = mapped_column(default=True)


class SkillCategory(Base):
    __tablename__ = "skill_category"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    name: Mapped[str] = mapped_column(unique=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class Skill(Base):
    __tablename__ = "skill"
    __table_args__ = (
        UniqueConstraint("category_id", "name"),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.skill_category.id")
    )
    name: Mapped[str]
    sort_order: Mapped[int] = mapped_column(default=0)


class SiteSetting(Base):
    __tablename__ = "site_setting"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    key: Mapped[str] = mapped_column(unique=True)
    # The about text is a JSON string, contact and impressum are objects.
    value: Mapped[str | dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime]
