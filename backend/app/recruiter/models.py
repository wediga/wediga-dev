"""Models of the recruiter links and the views recorded for them."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ACCESS_SCHEMA, UUID_DEFAULT, Base


class RecruiterLink(Base):
    __tablename__ = "recruiter_link"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    token_hash: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime]
    label: Mapped[str | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)


class LinkView(Base):
    __tablename__ = "link_view"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    recruiter_link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{ACCESS_SCHEMA}.recruiter_link.id")
    )
    viewed_at: Mapped[datetime]
    origin: Mapped[str]
