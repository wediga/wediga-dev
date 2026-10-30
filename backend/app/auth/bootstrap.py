"""Admin bootstrap from the environment.

On startup, with no ``admin`` row and ``ADMIN_PASSWORD`` set, one admin row
(id=1) is created from an argon2 hash. An existing row is left alone, so a
restart never overwrites the password. The raw password is never logged or
stored in plaintext.
"""

import os

from sqlalchemy import insert

from app.auth.models import ADMIN_ID, Admin
from app.auth.passwords import hash_password
from app.db.connection import get_session, now


def ensure_admin() -> bool:
    """Create the admin row from ``ADMIN_PASSWORD`` if none exists.

    Returns ``True`` when a row was created, ``False`` otherwise (already
    present, or no password configured).
    """
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        return False

    with get_session() as session:
        if session.get(Admin, ADMIN_ID) is not None:
            return False

        timestamp = now()
        session.execute(
            insert(Admin).values(
                id=ADMIN_ID,
                password_hash=hash_password(password),
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
        session.commit()

    return True
