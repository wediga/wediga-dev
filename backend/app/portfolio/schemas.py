"""Pydantic schemas of the portfolio.

The admin reads every synced repo with its entry and writes one entry at a
time, the recruiter view reads the published tiles. Texts are keyed by the
same fields as the texts from GitHub.
"""

import uuid
from typing import Annotated

from pydantic import BaseModel, Field

from app.content.schemas import LONG
from app.github.schemas import GithubRepoRead, GithubSyncRead, TextFieldKey

OwnText = Annotated[str, Field(max_length=LONG)]


class StatusRead(BaseModel):
    id: uuid.UUID
    key: str
    label: str


class EntryWrite(BaseModel):
    """An entry as the admin saves it. A blank text means none of its own."""

    project_status_id: uuid.UUID
    sort_order: int = 0
    published: bool
    texts: dict[TextFieldKey, OwnText] = Field(default_factory=dict)


class EntryRead(EntryWrite):
    # Published with own texts for some fields, but GitHub texts in others.
    partly_translated: bool


class PortfolioRepoRead(GithubRepoRead):
    entry: EntryRead | None


class PortfolioAdmin(BaseModel):
    """Every repo of the latest successful sync, published ones first."""

    last_sync: GithubSyncRead | None
    statuses: list[StatusRead]
    repos: list[PortfolioRepoRead]


class TileRead(BaseModel):
    """A published repo with its own text per field, else the one from GitHub."""

    id: uuid.UUID
    texts: dict[TextFieldKey, str]
    status: StatusRead
    archived: bool
    technologies: list[str]
    demo_url: str | None
    github_url: str
