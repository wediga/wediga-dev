"""Storage for the single uploaded CV PDF.

The PDF lives in the one row of ``cv_document``, so the nightly ``pg_dump``
covers it together with the rest of the data. A new upload replaces the row in
one transaction, so an interrupted upload never leaves the old CV missing.
"""

from sqlalchemy import delete, exists, select

from app.cv.models import CvDocument
from app.db.connection import get_session, now


def has_cv() -> bool:
    """Return whether a CV PDF is currently stored."""
    with get_session() as session:
        return bool(session.scalar(select(exists().select_from(CvDocument))))


def load_cv() -> bytes | None:
    """Return the stored PDF bytes, or None when no CV was uploaded yet."""
    with get_session() as session:
        return session.scalar(select(CvDocument.content))


def save_cv(data: bytes) -> None:
    """Store the PDF bytes, replacing any existing CV."""
    with get_session() as session:
        session.execute(delete(CvDocument))
        session.add(CvDocument(content=data, uploaded_at=now()))
        session.commit()
