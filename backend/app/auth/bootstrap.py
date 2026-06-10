"""Admin bootstrap from the environment.

On startup, if the ``admin`` table has no row and ``ADMIN_PASSWORD`` is set,
a single admin row (id=1) is created with an argon2 hash of the password.
If the row already exists, nothing happens, so a restart never overwrites the
password. The raw password is read only here, never logged and never stored
in plaintext.
"""

import os

from app.auth.passwords import hash_password
from app.db.connection import get_connection, now


def ensure_admin() -> bool:
    """Create the admin row from ``ADMIN_PASSWORD`` if none exists.

    Returns ``True`` when a row was created, ``False`` otherwise (already
    present, or no password configured).
    """
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        return False

    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM admin WHERE id = 1").fetchone()
        if existing is not None:
            return False
        timestamp = now()
        conn.execute(
            "INSERT INTO admin (id, password_hash, created_at, updated_at) "
            "VALUES (1, ?, ?, ?)",
            (hash_password(password), timestamp, timestamp),
        )
        conn.commit()
    return True
