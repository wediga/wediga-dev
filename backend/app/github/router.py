"""GitHub route for the admin: a sync on demand.

Nothing the sync stores is writable through a route, and the admin reads it
through the portfolio. The write uses the standard gate (see WRITE_DEPS).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.github import sync
from app.github.client import GithubApiError

router = APIRouter(prefix="/github", tags=["github"])

WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]


@router.post("/sync", dependencies=WRITE_DEPS)
def trigger_sync() -> dict:
    """Run a sync now, on demand from the admin.

    A GitHub failure becomes a clean 502 with no internal detail, and the repos
    of the last successful run stay as they are.
    """
    try:
        count = sync.sync_repos()
    except GithubApiError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub sync failed; the last successful sync stays in place",
        ) from None
    return {"ok": True, "synced": count}
