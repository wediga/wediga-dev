"""Pydantic schemas for the five content types.

Each type has read and write models. The write models carry length limits so
invalid input is rejected before anything touches the database. About,
contact and impressum are single values held in ``site_setting``; projects and
skills are collections in their own tables.
"""

from pydantic import BaseModel, Field, field_validator

# Generous but bounded limits. Free text is capped well above real content,
# short fields tightly, so a write can never store unbounded blobs.
SHORT = 200
MEDIUM = 500
LONG = 5000
TEXT = 50000


def _validate_web_link(value: str | None) -> str | None:
    """Allow only http(s) links, so a stored value can never carry a
    javascript: or data: scheme into an href on the rendered pages."""
    if value is None or value == "":
        return value
    lowered = value.strip().lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        raise ValueError("link must start with http:// or https://")
    return value


class AboutContent(BaseModel):
    """The About markdown text held under the ``about_text`` setting."""

    text: str = Field(max_length=TEXT)


class ContactContent(BaseModel):
    """Contact details held as a JSON blob under the ``contact`` setting."""

    name: str = Field(max_length=SHORT)
    email: str = Field(max_length=SHORT)
    github: str | None = Field(default=None, max_length=MEDIUM)
    linkedin: str | None = Field(default=None, max_length=MEDIUM)

    _check_links = field_validator("github", "linkedin")(_validate_web_link)


class ImpressumAddress(BaseModel):
    street: str = Field(max_length=SHORT)
    city: str = Field(max_length=SHORT)


class ImpressumContent(BaseModel):
    """Legal notice held as a JSON blob under the ``impressum`` setting."""

    name: str = Field(max_length=SHORT)
    email: str = Field(max_length=SHORT)
    github: str | None = Field(default=None, max_length=MEDIUM)
    linkedin: str | None = Field(default=None, max_length=MEDIUM)
    address: ImpressumAddress | None = None

    _check_links = field_validator("github", "linkedin")(_validate_web_link)


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
    id: int


class SkillRead(BaseModel):
    id: int
    name: str
    sort_order: int


class SkillCategoryWrite(BaseModel):
    name: str = Field(min_length=1, max_length=SHORT)
    sort_order: int = 0


class SkillCategoryRead(BaseModel):
    id: int
    name: str
    sort_order: int
    skills: list[SkillRead] = Field(default_factory=list)


class SkillWrite(BaseModel):
    name: str = Field(min_length=1, max_length=SHORT)
    sort_order: int = 0
