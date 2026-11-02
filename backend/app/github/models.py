"""Models of the public GitHub repos as the sync last saw them.

Only the sync writes these tables. A repo is kept by its GitHub id, so a
rename changes its name text and nothing else, and a repo that the last
successful sync did not see has an older ``last_seen_sync_id``.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base

GITHUB_REPO_ID = f"{SITE_SCHEMA}.github_repo.id"


class GithubSync(Base):
    """One run of the sync. It succeeded when it finished without an error."""

    __tablename__ = "github_sync"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(default=None)


class GithubRepo(Base):
    __tablename__ = "github_repo"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    homepage_url: Mapped[str | None]
    archived: Mapped[bool]
    last_seen_sync_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.github_sync.id")
    )


class TextField(Base):
    """One of the texts a portfolio tile shows, such as name or problem."""

    __tablename__ = "text_field"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    key: Mapped[str] = mapped_column(unique=True)


class GithubRepoText(Base):
    __tablename__ = "github_repo_text"
    __table_args__ = (
        UniqueConstraint("github_repo_id", "text_field_id"),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    github_repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(GITHUB_REPO_ID, ondelete="CASCADE")
    )
    text_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.text_field.id")
    )
    value: Mapped[str]


class GithubRepoTechnology(Base):
    """A topic of a repo, through the technology that carries its name."""

    __tablename__ = "github_repo_technology"
    __table_args__ = (
        UniqueConstraint("github_repo_id", "technology_id"),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    github_repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(GITHUB_REPO_ID, ondelete="CASCADE")
    )
    technology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.technology.id", ondelete="CASCADE")
    )
