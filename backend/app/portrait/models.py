"""Model of the single row that holds the uploaded portrait."""

import uuid

from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base


class Portrait(Base):
    """The image bytes and their crop: the point, in percent of width and
    height, that stays in view and the zoom around it, in percent."""

    __tablename__ = "portrait"
    # A unique index on a constant allows at most one row.
    __table_args__ = (
        Index("portrait_single_row", text("(true)"), unique=True),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    content: Mapped[bytes]
    focus_x: Mapped[int]
    focus_y: Mapped[int]
    zoom: Mapped[int]
