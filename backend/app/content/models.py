"""Models of the site content: projects, skills and the key-value settings."""

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(unique=True)
    tagline: Mapped[str | None] = mapped_column(default=None)
    problem: Mapped[str | None] = mapped_column(default=None)
    solution: Mapped[str | None] = mapped_column(default=None)
    learning: Mapped[str | None] = mapped_column(default=None)
    tech_stack: Mapped[str | None] = mapped_column(default=None)
    demo_link: Mapped[str | None] = mapped_column(default=None)
    github_link: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class SkillCategory(Base):
    __tablename__ = "skill_category"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(unique=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("skill_category.id"))
    name: Mapped[str]
    sort_order: Mapped[int] = mapped_column(default=0)


class SiteSetting(Base):
    __tablename__ = "site_setting"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]
    updated_at: Mapped[str]
