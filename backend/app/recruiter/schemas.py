"""Pydantic schemas for recruiter magic links.

A link carries a label and an optional expiry. The plaintext token leaves the
backend once, in the create response, and never again; the database holds only
its hash.
"""

from datetime import date

from pydantic import BaseModel, Field

LABEL_MAX = 200


class RecruiterLinkCreate(BaseModel):
    """A link as created from the admin."""

    label: str | None = Field(default=None, max_length=LABEL_MAX)
    # Valid through the end of this day in UTC; empty means never expires.
    expires_on: date | None = None


class RecruiterLinkRead(BaseModel):
    """A link with its call statistics for the admin list."""

    id: int
    label: str | None
    created_at: str
    expires_at: str | None
    revoked_at: str | None
    view_count: int
    last_viewed_at: str | None
    active: bool


class RecruiterLinkCreated(RecruiterLinkRead):
    """The create response, carrying the plaintext token shown only once."""

    token: str
