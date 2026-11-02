"""Pydantic schemas for the profile, projects and skills.

The write models carry length limits so oversized input is rejected before it
touches the database.
"""

import uuid
from typing import Annotated, Literal, get_args

from pydantic import AfterValidator, BaseModel, Field, field_validator

# Bounded limits so a write can never store an unbounded blob.
SHORT = 200
MEDIUM = 500
LONG = 5000
TEXT = 50000


def _validate_web_link(value: str | None) -> str | None:
    """Allow only http(s) links, so a stored value never carries a javascript:
    or data: scheme into an href on the rendered pages."""
    if value is None or value == "":
        return value
    lowered = value.strip().lower()
    if not lowered.startswith(("http://", "https://")):
        raise ValueError("link must start with http:// or https://")
    return value


# The kinds of link a profile can carry, one row each in ``link_kind``.
LinkKind = Literal["github", "linkedin"]
LINK_KINDS: tuple[str, ...] = get_args(LinkKind)

ProfileUrl = Annotated[
    str, Field(min_length=1, max_length=MEDIUM), AfterValidator(_validate_web_link)
]


class ProfileAddress(BaseModel):
    street: str = Field(max_length=SHORT)
    postal_code: str = Field(max_length=SHORT)
    city: str = Field(max_length=SHORT)


class ContactContent(BaseModel):
    """The contact view on the profile: name, email and links."""

    name: str = Field(max_length=SHORT)
    email: str = Field(max_length=SHORT)
    links: dict[LinkKind, ProfileUrl] = Field(default_factory=dict)


class ProfileContent(ContactContent):
    """The whole profile as the admin edits it."""

    about_md: str = Field(max_length=TEXT)
    address: ProfileAddress | None = None


class ImpressumContent(BaseModel):
    """The public impressum: only name and email, never the address."""

    name: str
    email: str


class ProjectWrite(BaseModel):
    """A project row as written from the admin."""

    name: str = Field(min_length=1, max_length=SHORT)
    tagline: str | None = Field(default=None, max_length=MEDIUM)
    problem: str | None = Field(default=None, max_length=LONG)
    solution: str | None = Field(default=None, max_length=LONG)
    learning: str | None = Field(default=None, max_length=LONG)
    tech_stack: list[str] = Field(default_factory=list, max_length=50)
    demo_link: str | None = Field(default=None, max_length=MEDIUM)
    github_link: str | None = Field(default=None, max_length=MEDIUM)
    status: str | None = Field(default=None, max_length=SHORT)
    sort_order: int = 0
    visible: bool = True

    _check_links = field_validator("demo_link", "github_link")(_validate_web_link)


class ProjectRead(ProjectWrite):
    id: uuid.UUID


class SkillRead(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int


class SkillCategoryWrite(BaseModel):
    name: str = Field(min_length=1, max_length=SHORT)
    sort_order: int = 0


class SkillCategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int
    skills: list[SkillRead] = Field(default_factory=list)


class SkillWrite(BaseModel):
    name: str = Field(min_length=1, max_length=SHORT)
    sort_order: int = 0
