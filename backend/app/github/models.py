"""Model of a mirrored GitHub repository together with its curation.

It keeps the shape the table had in SQLite, as a step towards the portfolio
from GitHub in the plan.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base


class GithubRepo(Base):
    __tablename__ = "github_repo"
    __table_args__ = ({"schema": SITE_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(default=None)
    language: Mapped[str | None] = mapped_column(default=None)
    stars: Mapped[int | None] = mapped_column(default=None)
    url: Mapped[str | None] = mapped_column(default=None)
    last_push: Mapped[datetime | None] = mapped_column(default=None)
    last_sync: Mapped[datetime | None] = mapped_column(default=None)
    visible: Mapped[bool] = mapped_column(default=True)
    pinned: Mapped[bool] = mapped_column(default=False)
    description_override: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
