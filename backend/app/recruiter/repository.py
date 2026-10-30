"""Read and write functions for recruiter links and their call tracking.

The token comes from ``secrets`` and only its SHA-256 hash reaches the
database, so a leak exposes no usable link. A fast hash is enough because a
256-bit random token is infeasible to guess, so a slow password hash would add
cost without buying security. The plaintext is returned once from
``create_link`` and never again. Every query goes through SQLAlchemy with bound
parameters, no SQL is built from input.
"""

import hashlib
import secrets
from datetime import UTC, date, datetime, time
from enum import Enum, auto

from sqlalchemy import RowMapping, func, select
from sqlalchemy.orm import Session

from app.db.connection import get_session, now
from app.recruiter.models import LinkView, RecruiterLink

# 32 url-safe random bytes, a 256-bit token.
_TOKEN_BYTES = 32


class LinkStatus(Enum):
    """State of a known link, as ``validate_token`` reports it."""

    OK = auto()
    REVOKED = auto()
    EXPIRED = auto()


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
    end_of_day = datetime.combine(expires_on, time(23, 59, 59), tzinfo=UTC)
    return end_of_day.isoformat()


def _is_expired(expires_at: str | None) -> bool:
    """Return whether an expiry instant has passed. No expiry never expires."""
    if expires_at is None:
        return False
    return datetime.fromisoformat(expires_at) <= datetime.now(UTC)


def _is_active(expires_at: str | None, revoked_at: str | None) -> bool:
    return revoked_at is None and not _is_expired(expires_at)


def _row_to_read(row: RowMapping) -> dict:
    return {
        **row,
        "active": _is_active(row["expires_at"], row["revoked_at"]),
    }


_SELECT_WITH_STATS = (
    select(
        RecruiterLink.id,
        RecruiterLink.label,
        RecruiterLink.created_at,
        RecruiterLink.expires_at,
        RecruiterLink.revoked_at,
        func.count(LinkView.id).label("view_count"),
        func.max(LinkView.viewed_at).label("last_viewed_at"),
    )
    .outerjoin(LinkView, LinkView.link_id == RecruiterLink.id)
    .group_by(RecruiterLink.id)
)


def _get_link(session: Session, link_id: int) -> dict | None:
    row = (
        session.execute(_SELECT_WITH_STATS.where(RecruiterLink.id == link_id))
        .mappings()
        .one_or_none()
    )
    return _row_to_read(row) if row is not None else None


def create_link(label: str | None, expires_on: date | None) -> tuple[dict, str]:
    """Create a link and return its read view together with the plaintext token."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)

    with get_session() as session:
        link = RecruiterLink(
            token=_hash_token(token),
            created_at=now(),
            label=label,
            expires_at=_expiry_iso(expires_on),
        )
        session.add(link)
        session.commit()
        read = _get_link(session, link.id)
        assert read is not None

    return read, token


def list_links() -> list[dict]:
    """Return every link with its view count and last view, newest first."""
    query = _SELECT_WITH_STATS.order_by(
        RecruiterLink.created_at.desc(), RecruiterLink.id.desc()
    )

    with get_session() as session:
        return [_row_to_read(row) for row in session.execute(query).mappings()]


def revoke_link(link_id: int) -> dict | None:
    """Revoke a link by stamping ``revoked_at``; return its read view or None.

    Idempotent: an already revoked link keeps its first revoke time, a missing
    link returns None so the router can answer 404.
    """
    with get_session() as session:
        link = session.get(RecruiterLink, link_id)

        if link is None:
            return None

        if link.revoked_at is None:
            link.revoked_at = now()
            session.commit()

        return _get_link(session, link_id)


def validate_token(token: str) -> tuple[LinkStatus, int] | None:
    """Look a token up by its hash and classify it.

    Returns the link's status together with its id, or ``None`` for an unknown
    token. The lookup matches on the stored hash, never the plaintext.
    """
    with get_session() as session:
        link: RecruiterLink | None = session.scalar(
            select(RecruiterLink).where(RecruiterLink.token == _hash_token(token))
        )

        if link is None:
            return None

        if link.revoked_at is not None:
            return LinkStatus.REVOKED, link.id

        if _is_expired(link.expires_at):
            return LinkStatus.EXPIRED, link.id

        return LinkStatus.OK, link.id


def link_is_active(link_id: int | None) -> bool:
    """Return whether the link behind a recruiter session is still usable.

    Called on every recruiter read, so revoking or expiring a link cuts an
    already redeemed session, not just a new redeem.
    """
    if not link_id:
        return False

    with get_session() as session:
        link = session.get(RecruiterLink, link_id)

        if link is None:
            return False

        return _is_active(link.expires_at, link.revoked_at)


def record_view(link_id: int, origin: str) -> None:
    """Write one row to ``link_view`` for a valid redeem."""
    with get_session() as session:
        session.add(LinkView(link_id=link_id, viewed_at=now(), origin=origin))
        session.commit()
