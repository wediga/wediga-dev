"""Model of the single row that holds the uploaded CV PDF."""

import uuid
from datetime import datetime

from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import SITE_SCHEMA, UUID_DEFAULT, Base


class CvDocument(Base):
    __tablename__ = "cv_document"
    # A unique index on a constant allows at most one row.
    __table_args__ = (
        Index("cv_document_single_row", text("(true)"), unique=True),
        {"schema": SITE_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    content: Mapped[bytes]
    uploaded_at: Mapped[datetime]
