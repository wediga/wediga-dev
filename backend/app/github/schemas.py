"""Pydantic schemas for the GitHub repo layer.

A repo row splits into mirrored fields (from GitHub, overwritten every sync)
and curation fields (admin-owned, never touched by the sync). The schemas keep
that split: ``GithubRepoRead`` is the full admin view, ``GithubRepoPublic`` the
curated recruiter view, ``RepoCurationWrite`` the four curation fields a write
may change.
"""

from pydantic import BaseModel, Field

OVERRIDE_MAX = 500


class GithubRepoRead(BaseModel):
    """The full repo row for the admin, mirrored fields plus curation."""

    id: int
    name: str
    description: str | None
    language: str | None
    stars: int | None
    url: str | None
    last_push: str | None
    last_sync: str | None
    visible: bool
    pinned: bool
    description_override: str | None
    sort_order: int


class GithubRepoPublic(BaseModel):
    """The curated repo as the recruiter view sees it.

    ``description`` is the effective text the repository layer resolves: the
    admin override when set, else the mirrored GitHub description.
    """

    name: str
    description: str | None
    language: str | None
    stars: int | None
    url: str | None
    last_push: str | None
    pinned: bool


class RepoCurationWrite(BaseModel):
    """The curation fields the admin may set on a repo.

    The mirrored fields are never accepted from a request, so a write cannot
    spoof the GitHub-sourced data.
    """

    visible: bool = True
    pinned: bool = False
    description_override: str | None = Field(default=None, max_length=OVERRIDE_MAX)
    sort_order: int = 0
