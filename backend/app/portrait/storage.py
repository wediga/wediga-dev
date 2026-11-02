"""Storage for the single uploaded portrait.

A new upload replaces the row in one transaction and starts uncropped, because
the crop of the old image says nothing about the new one.
"""

from sqlalchemy import delete, select, update

from app.db.connection import get_session
from app.portrait.models import Portrait
from app.portrait.schemas import FOCUS_CENTER, ZOOM_MIN, PortraitCrop


def load_portrait() -> bytes | None:
    """Return the stored image bytes, or None when no portrait was uploaded."""
    with get_session() as session:
        return session.scalar(select(Portrait.content))


def load_crop() -> PortraitCrop | None:
    """Return the crop of the stored portrait, or None without a portrait."""
    with get_session() as session:
        row = session.execute(
            select(Portrait.focus_x, Portrait.focus_y, Portrait.zoom)
        ).first()

    if row is None:
        return None

    return PortraitCrop(x=row.focus_x, y=row.focus_y, zoom=row.zoom)


def save_portrait(data: bytes) -> PortraitCrop:
    """Store the image bytes, replacing any existing portrait, and return the
    crop it starts with."""
    crop = PortraitCrop(x=FOCUS_CENTER, y=FOCUS_CENTER, zoom=ZOOM_MIN)

    with get_session() as session:
        session.execute(delete(Portrait))
        session.add(
            Portrait(content=data, focus_x=crop.x, focus_y=crop.y, zoom=crop.zoom)
        )
        session.commit()

    return crop


def save_crop(crop: PortraitCrop) -> bool:
    """Store the crop of the portrait. False when there is no portrait."""
    with get_session() as session:
        updated = session.scalar(
            update(Portrait)
            .values(focus_x=crop.x, focus_y=crop.y, zoom=crop.zoom)
            .returning(Portrait.id)
        )
        session.commit()

    return updated is not None
