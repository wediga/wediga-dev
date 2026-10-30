"""Model of the single admin row behind the password login."""

from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Admin(Base):
    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]
    totp_secret: Mapped[str | None]
    totp_enabled: Mapped[bool] = mapped_column(Boolean)
