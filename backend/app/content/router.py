"""Content routes: public reads and admin-protected writes.

Reads are public GET endpoints so the Server Components can render the site.
Writes (create, update, delete) sit behind ``require_admin`` for the session
and ``require_csrf`` for the synchronizer token, so a write without a session
is 401 and a write without a valid token is 403.
"""

from fastapi import APIRouter, Depends, status

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.content import repository as repo
from app.errors import not_found
from app.recruiter.dependencies import require_recruiter_view
from app.content.schemas import (
    AboutContent,
    ContactContent,
    ImpressumContent,
    ProjectRead,
    ProjectWrite,
    SkillCategoryRead,
    SkillCategoryWrite,
    SkillRead,
    SkillWrite,
)

router = APIRouter(prefix="/content", tags=["content"])

# Writes need both an admin session and a valid CSRF token.
WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]

# Recruiter-facing reads (the full portfolio and the contact details) sit
# behind the recruiter gate, which an admin session also satisfies and which
# re-checks the link state, so a revoked or expired link loses access. About
# and skills stay public because they feed the public landing page, and the
# public impressum keeps its own name-and-email split.
RECRUITER_READ_DEPS = [Depends(require_recruiter_view)]

NOT_FOUND = not_found()


# --- about ---------------------------------------------------------------


@router.get("/about", response_model=AboutContent)
def read_about() -> AboutContent:
    text = repo.get_about()
    return AboutContent(text=text if text is not None else "")


@router.put("/about", response_model=AboutContent, dependencies=WRITE_DEPS)
def write_about(body: AboutContent) -> AboutContent:
    repo.set_about(body.text)
    return body


@router.delete("/about", dependencies=WRITE_DEPS)
def remove_about() -> dict[str, bool]:
    # Delete is idempotent: removing absent content is still a success.
    repo.delete_about()
    return {"ok": True}


# --- contact -------------------------------------------------------------


@router.get(
    "/contact",
    response_model=ContactContent | None,
    dependencies=RECRUITER_READ_DEPS,
)
def read_contact() -> ContactContent | None:
    data = repo.get_contact()
    return ContactContent(**data) if data is not None else None


@router.put("/contact", response_model=ContactContent, dependencies=WRITE_DEPS)
def write_contact(body: ContactContent) -> ContactContent:
    repo.set_contact(body)
    return body


@router.delete("/contact", dependencies=WRITE_DEPS)
def remove_contact() -> dict[str, bool]:
    repo.delete_contact()
    return {"ok": True}


# --- impressum -----------------------------------------------------------


@router.get("/impressum", response_model=ImpressumContent | None)
def read_impressum() -> ImpressumContent | None:
    """Public read: only name and email, matching the documented split."""
    data = repo.get_impressum()
    if data is None:
        return None
    return ImpressumContent(name=data.get("name", ""), email=data.get("email", ""))


@router.get(
    "/admin/impressum",
    response_model=ImpressumContent | None,
    dependencies=[Depends(require_admin)],
)
def read_full_impressum() -> ImpressumContent | None:
    """Admin read: the full legal record for the editor."""
    data = repo.get_impressum()
    return ImpressumContent(**data) if data is not None else None


@router.put("/impressum", response_model=ImpressumContent, dependencies=WRITE_DEPS)
def write_impressum(body: ImpressumContent) -> ImpressumContent:
    repo.set_impressum(body)
    return body


@router.delete("/impressum", dependencies=WRITE_DEPS)
def remove_impressum() -> dict[str, bool]:
    repo.delete_impressum()
    return {"ok": True}


# --- projects ------------------------------------------------------------


@router.get(
    "/projects",
    response_model=list[ProjectRead],
    dependencies=RECRUITER_READ_DEPS,
)
def read_projects() -> list[dict]:
    """Recruiter read: only visible projects, gated behind the recruiter view."""
    return repo.list_projects(include_hidden=False)


@router.get(
    "/admin/projects",
    response_model=list[ProjectRead],
    dependencies=[Depends(require_admin)],
)
def read_all_projects() -> list[dict]:
    """Admin read: every project, including hidden ones."""
    return repo.list_projects(include_hidden=True)


@router.post(
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=WRITE_DEPS,
)
def create_project(body: ProjectWrite) -> dict:
    return repo.create_project(body)


@router.put("/projects/{project_id}", response_model=ProjectRead, dependencies=WRITE_DEPS)
def update_project(project_id: int, body: ProjectWrite) -> dict:
    updated = repo.update_project(project_id, body)
    if updated is None:
        raise NOT_FOUND
    return updated


@router.delete("/projects/{project_id}", dependencies=WRITE_DEPS)
def delete_project(project_id: int) -> dict[str, bool]:
    if not repo.delete_project(project_id):
        raise NOT_FOUND
    return {"ok": True}


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
def update_category(category_id: int, body: SkillCategoryWrite) -> dict:
    updated = repo.update_category(category_id, body)
    if updated is None:
        raise NOT_FOUND
    return updated


@router.delete("/skills/categories/{category_id}", dependencies=WRITE_DEPS)
def delete_category(category_id: int) -> dict[str, bool]:
    if not repo.delete_category(category_id):
        raise NOT_FOUND
    return {"ok": True}


@router.post(
    "/skills/categories/{category_id}/skills",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=WRITE_DEPS,
)
def create_skill(category_id: int, body: SkillWrite) -> dict:
    created = repo.create_skill(category_id, body)
    if created is None:
        raise NOT_FOUND
    return created


@router.put("/skills/{skill_id}", response_model=SkillRead, dependencies=WRITE_DEPS)
def update_skill(skill_id: int, body: SkillWrite) -> dict:
    updated = repo.update_skill(skill_id, body)
    if updated is None:
        raise NOT_FOUND
    return updated


@router.delete("/skills/{skill_id}", dependencies=WRITE_DEPS)
def delete_skill(skill_id: int) -> dict[str, bool]:
    if not repo.delete_skill(skill_id):
        raise NOT_FOUND
    return {"ok": True}
