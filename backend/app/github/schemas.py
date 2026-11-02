"""Pydantic schemas for the GitHub layer.

``SyncedRepo`` is one public repo as the client hands it to the sync, checked
where it arrives from the API. ``GithubOverview`` is what the admin sees of the
last sync. The texts of a repo are keyed by ``TextFieldKey``, one row each in
``text_field``.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field

from app.content.schemas import TOPIC_MAX, TOPIC_PATTERN

# The texts a portfolio tile shows. Name and description come from the repo,
# the others from fixed sections of its README.
TextFieldKey = Literal[
    "name", "description", "problem", "solution", "learning", "ending"
]
TEXT_FIELDS: tuple[str, ...] = get_args(TextFieldKey)

Topic = Annotated[str, Field(pattern=TOPIC_PATTERN, max_length=TOPIC_MAX)]


class SyncedRepo(BaseModel):
    """One public repo with everything the sync stores about it."""

    github_id: int
    homepage_url: str | None
    archived: bool
    topics: list[Topic]
    texts: dict[TextFieldKey, str]


class GithubSyncRead(BaseModel):
    started_at: datetime
    finished_at: datetime | None
    error: str | None


class GithubRepoRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    homepage_url: str | None
    archived: bool
    technologies: list[str]


class GithubOverview(BaseModel):
    """The latest sync, and the repos of the latest one that succeeded."""

    last_sync: GithubSyncRead | None
    repos: list[GithubRepoRead]
