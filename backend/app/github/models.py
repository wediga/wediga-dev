"""Model of a mirrored GitHub repository together with its curation."""

from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GithubRepo(Base):
    __tablename__ = "github_repo"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    language: Mapped[str | None]
    stars: Mapped[int | None]
    url: Mapped[str | None]
    last_push: Mapped[str | None]
    last_sync: Mapped[str | None]
    visible: Mapped[bool] = mapped_column(Boolean)
    pinned: Mapped[bool] = mapped_column(Boolean)
    description_override: Mapped[str | None]
    sort_order: Mapped[int]
