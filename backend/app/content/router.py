"""Content routes: public reads and admin-protected writes.

Skills and the impressum are public so the Server Components render the
public site. Contact and impressum are views on the profile that each copy
only what they may show, so the address never leaves through them.
Writes and recruiter reads use the standard gates (see WRITE_DEPS and
``require_recruiter_view``).
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.content import repository as repo
from app.content.schemas import (
    ContactContent,
    ImpressumContent,
    ProfileContent,
    SkillCategoryRead,
    SkillCategoryWrite,
    TechnologyRead,
    TechnologyWrite,
)
from app.errors import not_found
from app.recruiter.dependencies import require_recruiter_view

router = APIRouter(prefix="/content", tags=["content"])

WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]
RECRUITER_READ_DEPS = [Depends(require_recruiter_view)]

NOT_FOUND = not_found()


# --- profile and its views ----------------------------------------------


@router.get(
    "/profile",
    response_model=ProfileContent | None,
    dependencies=[Depends(require_admin)],
)
def read_profile() -> ProfileContent | None:
    return repo.get_profile()


@router.put("/profile", response_model=ProfileContent, dependencies=WRITE_DEPS)
def write_profile(body: ProfileContent) -> ProfileContent:
    repo.set_profile(body)

    return body


@router.get(
    "/contact",
    response_model=ContactContent | None,
    dependencies=RECRUITER_READ_DEPS,
)
def read_contact() -> ContactContent | None:
    profile = repo.get_profile()

    if profile is None:
        return None

    return ContactContent(name=profile.name, email=profile.email, links=profile.links)


@router.get("/impressum", response_model=ImpressumContent | None)
def read_impressum() -> ImpressumContent | None:
    profile = repo.get_profile()

    if profile is None:
        return None

    return ImpressumContent(name=profile.name, email=profile.email)


# --- skills --------------------------------------------------------------


@router.get("/skills", response_model=list[SkillCategoryRead])
def read_skills() -> list[dict]:
    return repo.list_skill_categories()


@router.post(
    "/skills/categories",
    response_model=SkillCategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=WRITE_DEPS,
)
def create_category(body: SkillCategoryWrite) -> dict:
    return repo.create_category(body)


@router.put(
    "/skills/categories/{category_id}",
    response_model=SkillCategoryRead,
    dependencies=WRITE_DEPS,
)
def update_category(category_id: uuid.UUID, body: SkillCategoryWrite) -> dict:
    updated = repo.update_category(category_id, body)
    if updated is None:
        raise NOT_FOUND
    return updated


@router.delete("/skills/categories/{category_id}", dependencies=WRITE_DEPS)
def delete_category(category_id: uuid.UUID) -> dict[str, bool]:
    if not repo.delete_category(category_id):
        raise NOT_FOUND
    return {"ok": True}


# --- technologies --------------------------------------------------------


@router.get(
    "/technologies",
    response_model=list[TechnologyRead],
    dependencies=[Depends(require_admin)],
)
def read_technologies() -> list[dict]:
    return repo.list_technologies()


@router.post(
    "/technologies",
    response_model=TechnologyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=WRITE_DEPS,
)
def create_technology(body: TechnologyWrite) -> dict:
    return repo.create_technology(body)


@router.put(
    "/technologies/{technology_id}",
    response_model=TechnologyRead,
    dependencies=WRITE_DEPS,
)
def update_technology(technology_id: uuid.UUID, body: TechnologyWrite) -> dict:
    updated = repo.update_technology(technology_id, body)

    if updated is None:
        raise NOT_FOUND

    return updated


@router.delete("/technologies/{technology_id}", dependencies=WRITE_DEPS)
def delete_technology(technology_id: uuid.UUID) -> dict[str, bool]:
    if not repo.delete_technology(technology_id):
        raise NOT_FOUND

    return {"ok": True}
