"""Model of the single admin row behind the password login."""

import uuid
from datetime import datetime

from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ACCESS_SCHEMA, UUID_DEFAULT, Base


class Admin(Base):
    __tablename__ = "admin"
    # A unique index on a constant allows at most one row.
    __table_args__ = (
        Index("admin_single_row", text("(true)"), unique=True),
        {"schema": ACCESS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    password_hash: Mapped[str]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    totp_secret: Mapped[str | None] = mapped_column(default=None)
    totp_enabled: Mapped[bool] = mapped_column(default=False)
