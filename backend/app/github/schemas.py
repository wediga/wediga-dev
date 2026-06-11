"""Pydantic schemas for the GitHub repo layer.

A repo row carries two kinds of fields. The mirrored fields come from GitHub
and are overwritten by every sync (description, language, stars, url, last
push, last sync). The curation fields are owned by the admin and the sync
never touches them (visible, pinned, description override, sort order). The
schemas keep that split visible: ``GithubRepoRead`` is the full admin view,
``GithubRepoPublic`` is the curated recruiter view, and ``RepoCurationWrite``
carries only the four curation fields a write may change.
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

    ``description`` here is the effective text: the admin override when set,
    otherwise the mirrored GitHub description. The repository layer resolves
    that, so the view never has to know about the override field.
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

    Only these four are writable. The mirrored fields are never accepted from
    a request, so a write can never spoof the GitHub-sourced data.
    """

    visible: bool = True
    pinned: bool = False
    description_override: str | None = Field(default=None, max_length=OVERRIDE_MAX)
    sort_order: int = 0
