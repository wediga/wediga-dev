"""Pydantic schemas for recruiter magic links.

A link carries a label and an expiry, by default one year after its creation.
The plaintext token leaves the backend once, in the create response, and never
again; the database holds only its hash.
"""

import uuid
from datetime import date, datetime, timedelta

from pydantic import BaseModel, Field

from app.db.connection import now

LABEL_MAX = 200
DEFAULT_LINK_LIFETIME = timedelta(days=365)


def _default_expiry() -> date:
    return (now() + DEFAULT_LINK_LIFETIME).date()


class RecruiterLinkCreate(BaseModel):
    """A link as created from the admin."""

    label: str | None = Field(default=None, max_length=LABEL_MAX)
    # Valid through the end of this day in UTC. Left out, the link gets the
    # default lifetime, and null means it never expires.
    expires_on: date | None = Field(default_factory=_default_expiry)


class RecruiterLinkExpiry(BaseModel):
    """A new expiry for an existing link, null removes it."""

    expires_on: date | None


class RecruiterLinkRead(BaseModel):
    """A link with its call statistics for the admin list."""

    id: uuid.UUID
    label: str | None
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    view_count: int
    last_viewed_at: datetime | None
    active: bool


class RecruiterLinkCreated(RecruiterLinkRead):
    """The create response, carrying the plaintext token shown only once."""

    token: str
