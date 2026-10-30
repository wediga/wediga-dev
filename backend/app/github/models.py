"""Model of a mirrored GitHub repository together with its curation."""

from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GithubRepo(Base):
    __tablename__ = "github_repo"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(default=None)
    language: Mapped[str | None] = mapped_column(default=None)
    stars: Mapped[int | None] = mapped_column(default=None)
    url: Mapped[str | None] = mapped_column(default=None)
    last_push: Mapped[str | None] = mapped_column(default=None)
    last_sync: Mapped[str | None] = mapped_column(default=None)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    description_override: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
