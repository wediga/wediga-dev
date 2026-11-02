"""Models of the site content: the profile, technologies and skills."""

import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base

# The links and the address of the profile go away together with it.
PROFILE_ID = f"{SITE_SCHEMA}.profile.id"


class SkillCategory(Base):
    __tablename__ = "skill_category"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    name: Mapped[str] = mapped_column(unique=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class Technology(Base):
    """A technology by its GitHub topic, the single place for its shown name."""

    __tablename__ = "technology"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    topic: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]


class Skill(Base):
    """A technology shown in a category. The unique reference keeps a
    technology in at most one category."""

    __tablename__ = "skill"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    skill_category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.skill_category.id")
    )
    technology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.technology.id", ondelete="CASCADE"), unique=True
    )
    sort_order: Mapped[int] = mapped_column(default=0)


class Profile(Base):
    """The person behind the site. Contact, impressum and about are views on
    this single row."""

    __tablename__ = "profile"
    # A unique index on a constant allows at most one row.
    __table_args__ = (
        Index("profile_single_row", text("(true)"), unique=True),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    name: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str]
    about_md: Mapped[str]


class LinkKind(Base):
    __tablename__ = "link_kind"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    key: Mapped[str] = mapped_column(unique=True)


class ProfileLink(Base):
    __tablename__ = "profile_link"
    __table_args__ = (
        UniqueConstraint("profile_id", "link_kind_id"),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(PROFILE_ID, ondelete="CASCADE")
    )
    link_kind_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.link_kind.id")
    )
    url: Mapped[str]


class PostalAddress(Base):
    __tablename__ = "postal_address"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(PROFILE_ID, ondelete="CASCADE"), unique=True
    )
    street: Mapped[str]
    postal_code: Mapped[str]
    city: Mapped[str]
