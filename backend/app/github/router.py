"""GitHub routes: admin curation and the curated recruiter read.

The admin endpoints (list every repo, set curation, trigger a sync) sit behind
``require_admin`` and, for the writes, ``require_csrf``, the same protection the
content and recruiter writes use. The curated list is a recruiter read behind
``require_recruiter_view``, which an admin session also satisfies and which
re-checks the link state. The mirrored fields are never writable through any
route, only the four curation fields are.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.github import repository as repo
from app.github import sync
from app.github.client import GithubApiError
from app.github.schemas import (
    GithubRepoPublic,
    GithubRepoRead,
    RepoCurationWrite,
)
from app.recruiter.dependencies import require_recruiter_view

router = APIRouter(prefix="/github", tags=["github"])

# Writes need both an admin session and a valid CSRF token.
WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get(
    "/admin/repos",
    response_model=list[GithubRepoRead],
    dependencies=[Depends(require_admin)],
)
def list_admin_repos() -> list[dict]:
    """Admin read: every repo with its mirrored and curation fields."""
    return repo.list_all()


@router.get(
    "/repos",
    response_model=list[GithubRepoPublic],
    dependencies=[Depends(require_recruiter_view)],
)
def list_curated_repos() -> list[dict]:
    """Recruiter read: the curated, visible repos, pinned first."""
    return repo.list_curated()


@router.put(
    "/repos/{repo_id}/curation",
    response_model=GithubRepoRead,
    dependencies=WRITE_DEPS,
)
def update_curation(repo_id: int, body: RepoCurationWrite) -> dict:
    """Set the curation of one repo (visible, pinned, override, sort order)."""
    updated = repo.update_curation(repo_id, body)
    if updated is None:
        raise NOT_FOUND
    return updated


@router.post("/sync", dependencies=WRITE_DEPS)
def trigger_sync() -> dict:
    """Run a sync now, on demand from the admin.

    A GitHub failure becomes a clean 502 with no internal detail, and the
    existing cache is left intact because nothing is written on failure.
    """
    try:
        count = sync.sync_repos()
    except GithubApiError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub sync failed; the existing cache is unchanged",
        )
    return {"ok": True, "synced": count}
