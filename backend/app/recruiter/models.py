"""Models of the recruiter links and the views recorded for them."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecruiterLink(Base):
    __tablename__ = "recruiter_link"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    token: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[str]
    label: Mapped[str | None] = mapped_column(default=None)
    expires_at: Mapped[str | None] = mapped_column(default=None)
    revoked_at: Mapped[str | None] = mapped_column(default=None)


class LinkView(Base):
    __tablename__ = "link_view"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    link_id: Mapped[int] = mapped_column(ForeignKey("recruiter_link.id"))
    viewed_at: Mapped[str]
    origin: Mapped[str | None] = mapped_column(default=None)
