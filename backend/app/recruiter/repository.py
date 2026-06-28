"""Read and write functions for recruiter links and their call tracking.

The token comes from ``secrets`` and only its SHA-256 hash reaches the
database, so a leak exposes no usable link. A fast hash is enough because a
256-bit random token is infeasible to guess, so a slow password hash would add
cost without buying security. The plaintext is returned once from
``create_link`` and never again. Every query is parameterised, no SQL is built
from input.
"""

import hashlib
import secrets
from datetime import date, datetime, time, timezone

from app.db.connection import get_connection, now

# 32 url-safe random bytes, a 256-bit token.
_TOKEN_BYTES = 32


def _hash_token(token: str) -> str:
    """Return the hex SHA-256 of a plaintext token for storage and lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _expiry_iso(expires_on: date | None) -> str | None:
    """Turn a calendar day into an end-of-day UTC timestamp, or ``None``.

    A link stays valid through the whole chosen day, so the stored instant is
    that day at 23:59:59 UTC.
    """
    if expires_on is None:
        return None
    end_of_day = datetime.combine(expires_on, time(23, 59, 59), tzinfo=timezone.utc)
    return end_of_day.isoformat()


def _is_expired(expires_at: str | None) -> bool:
    """Return whether an expiry instant has passed. No expiry never expires."""
    if expires_at is None:
        return False
    return datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc)


def _is_active(expires_at: str | None, revoked_at: str | None) -> bool:
    return revoked_at is None and not _is_expired(expires_at)


def _row_to_read(row) -> dict:
    return {
        "id": row["id"],
        "label": row["label"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "revoked_at": row["revoked_at"],
        "view_count": row["view_count"],
        "last_viewed_at": row["last_viewed_at"],
        "active": _is_active(row["expires_at"], row["revoked_at"]),
    }


_SELECT_WITH_STATS = (
    "SELECT rl.id, rl.label, rl.created_at, rl.expires_at, rl.revoked_at, "
    "COUNT(lv.id) AS view_count, MAX(lv.viewed_at) AS last_viewed_at "
    "FROM recruiter_link rl "
    "LEFT JOIN link_view lv ON lv.link_id = rl.id "
)


def _get_link(conn, link_id: int) -> dict | None:
    row = conn.execute(
        _SELECT_WITH_STATS + "WHERE rl.id = ? GROUP BY rl.id", (link_id,)
    ).fetchone()
    return _row_to_read(row) if row is not None else None


def create_link(label: str | None, expires_on: date | None) -> tuple[dict, str]:
    """Create a link and return its read view together with the plaintext token."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO recruiter_link (token, label, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_hash_token(token), label, now(), _expiry_iso(expires_on)),
        )
        conn.commit()
        link = _get_link(conn, cursor.lastrowid)
    return link, token  # type: ignore[return-value]


def list_links() -> list[dict]:
    """Return every link with its view count and last view, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            _SELECT_WITH_STATS + "GROUP BY rl.id ORDER BY rl.created_at DESC, rl.id DESC"
        ).fetchall()
    return [_row_to_read(row) for row in rows]


def revoke_link(link_id: int) -> dict | None:
    """Revoke a link by stamping ``revoked_at``; return its read view or None.

    Idempotent: an already revoked link keeps its first revoke time, a missing
    link returns None so the router can answer 404.
    """
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM recruiter_link WHERE id = ?", (link_id,)
        ).fetchone()
        if exists is None:
            return None
        conn.execute(
            "UPDATE recruiter_link SET revoked_at = ? "
            "WHERE id = ? AND revoked_at IS NULL",
            (now(), link_id),
        )
        conn.commit()
        return _get_link(conn, link_id)


def validate_token(token: str) -> tuple[str, int | None]:
    """Look a token up by its hash and classify it.

    Returns ``("ok", id)``, ``("revoked", id)``, ``("expired", id)`` or
    ``("invalid", None)``. The lookup matches on the stored hash, never the
    plaintext.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, expires_at, revoked_at FROM recruiter_link WHERE token = ?",
            (_hash_token(token),),
        ).fetchone()
    if row is None:
        return "invalid", None
    if row["revoked_at"] is not None:
        return "revoked", row["id"]
    if _is_expired(row["expires_at"]):
        return "expired", row["id"]
    return "ok", row["id"]


def link_is_active(link_id: int | None) -> bool:
    """Return whether the link behind a recruiter session is still usable.

    Called on every recruiter read, so revoking or expiring a link cuts an
    already redeemed session, not just a new redeem.
    """
    if not link_id:
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT expires_at, revoked_at FROM recruiter_link WHERE id = ?",
            (link_id,),
        ).fetchone()
    if row is None:
        return False
    return _is_active(row["expires_at"], row["revoked_at"])


def record_view(link_id: int, origin: str) -> None:
    """Write one row to ``link_view`` for a valid redeem."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO link_view (link_id, viewed_at, origin) VALUES (?, ?, ?)",
            (link_id, now(), origin),
        )
        conn.commit()
