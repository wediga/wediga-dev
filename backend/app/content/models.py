"""Models of the site content: projects, skills and the key-value settings."""

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    tagline: Mapped[str | None]
    problem: Mapped[str | None]
    solution: Mapped[str | None]
    learning: Mapped[str | None]
    tech_stack: Mapped[str | None]
    demo_link: Mapped[str | None]
    github_link: Mapped[str | None]
    status: Mapped[str | None]
    sort_order: Mapped[int]
    visible: Mapped[bool] = mapped_column(Boolean)


class SkillCategory(Base):
    __tablename__ = "skill_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    sort_order: Mapped[int]


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("skill_category.id"))
    name: Mapped[str]
    sort_order: Mapped[int]


class SiteSetting(Base):
    __tablename__ = "site_setting"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]
    updated_at: Mapped[str]
