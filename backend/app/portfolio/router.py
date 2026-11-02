"""Portfolio routes: the tiles for the recruiter view, the admin list and the
write of one entry. Reads and writes use the standard gates (see WRITE_DEPS
and ``require_recruiter_view``).
"""

import uuid

from fastapi import APIRouter, Depends

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.errors import not_found
from app.portfolio import repository as repo
from app.portfolio.schemas import EntryWrite, PortfolioAdmin, TileRead
from app.recruiter.dependencies import require_recruiter_view

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]


@router.get(
    "",
    response_model=list[TileRead],
    dependencies=[Depends(require_recruiter_view)],
)
def read_tiles() -> list[dict]:
    return repo.tiles()


@router.get(
    "/admin",
    response_model=PortfolioAdmin,
    dependencies=[Depends(require_admin)],
)
def read_admin() -> dict:
    return repo.admin_overview()


@router.put("/admin/repos/{repo_id}", dependencies=WRITE_DEPS)
def write_entry(repo_id: uuid.UUID, body: EntryWrite) -> dict[str, bool]:
    if not repo.save_entry(repo_id, body):
        raise not_found()

    return {"ok": True}
