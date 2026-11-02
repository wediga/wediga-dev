"""Models of the portfolio: which repos are shown, with which status and texts.

Only the admin writes these tables. An entry with an empty ``published_at`` is
not public and keeps its own texts for a later release.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base
from app.github.models import GITHUB_REPO_ID


class ProjectStatus(Base):
    """A status the admin picks for a tile. The migration writes the rows."""

    __tablename__ = "project_status"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    key: Mapped[str] = mapped_column(unique=True)
    label: Mapped[str]
    sort_order: Mapped[int]


class PortfolioEntry(Base):
    __tablename__ = "portfolio_entry"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    github_repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(GITHUB_REPO_ID, ondelete="CASCADE"), unique=True
    )
    project_status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.project_status.id")
    )
    sort_order: Mapped[int] = mapped_column(default=0)
    published_at: Mapped[datetime | None] = mapped_column(default=None)


class PortfolioTextOverride(Base):
    """An own text for one field of an entry, shown instead of the one from
    GitHub."""

    __tablename__ = "portfolio_text_override"
    __table_args__ = (
        UniqueConstraint("portfolio_entry_id", "text_field_id"),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    portfolio_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.portfolio_entry.id", ondelete="CASCADE")
    )
    text_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SITE_SCHEMA}.text_field.id")
    )
    value: Mapped[str]
