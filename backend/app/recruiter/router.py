"""Recruiter routes: admin link management and the public redeem endpoint.

Redeem is public because a recruiter has no session yet, and it is rate-limited.
Its recruiter marker is separate from the admin one, so redeeming never grants
admin. The admin endpoints use the standard write gate (see WRITE_DEPS).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.csrf import require_csrf
from app.auth.dependencies import require_admin
from app.auth.ratelimit import client_ip, redeem_limiter
from app.auth.sessions import RECRUITER_SESSION_KEY
from app.errors import not_found
from app.recruiter import repository as repo
from app.recruiter.dependencies import require_recruiter_view
from app.recruiter.schemas import (
    RecruiterLinkCreate,
    RecruiterLinkCreated,
    RecruiterLinkRead,
)
from app.recruiter.tracking import coarse_origin

router = APIRouter(prefix="/recruiter", tags=["recruiter"])

WRITE_DEPS = [Depends(require_admin), Depends(require_csrf)]


@router.post(
    "/links",
    response_model=RecruiterLinkCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=WRITE_DEPS,
)
def create_link(body: RecruiterLinkCreate) -> dict:
    """Create a link and return it once with the plaintext token."""
    link, token = repo.create_link(body.label, body.expires_on)
    return {**link, "token": token}


@router.get(
    "/links",
    response_model=list[RecruiterLinkRead],
    dependencies=[Depends(require_admin)],
)
def list_links() -> list[dict]:
    """List every link with its view count and last view."""
    return repo.list_links()


@router.post(
    "/links/{link_id}/revoke",
    response_model=RecruiterLinkRead,
    dependencies=WRITE_DEPS,
)
def revoke_link(link_id: int) -> dict:
    """Revoke a link, which blocks any further redeem."""
    link = repo.revoke_link(link_id)
    if link is None:
        raise not_found("Link not found")
    return link


@router.post("/redeem/{token}")
def redeem(token: str, request: Request) -> dict[str, bool]:
    """Validate a token, start the recruiter session and record the view.

    Unknown token is 404, revoked or expired is 410. On success the recruiter
    marker is set fresh (no fixation carry-over) and one view row is written
    with only the coarse origin. The per-IP rate limit caps request floods and
    view-count inflation from one source.
    """
    if not redeem_limiter.hit(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, try again later",
        )

    result, link_id = repo.validate_token(token)
    if result == "invalid":
        raise not_found("Link not found")
    if result in ("revoked", "expired"):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Link no longer valid"
        )

    request.session[RECRUITER_SESSION_KEY] = link_id
    repo.record_view(link_id, coarse_origin(client_ip(request)))  # type: ignore[arg-type]
    return {"ok": True}


@router.get("/session", dependencies=[Depends(require_recruiter_view)])
def session_check() -> dict[str, bool]:
    """Return success when a recruiter or admin session is active and valid.

    The recruiter route group calls this server-side to gate its pages, like
    the admin layout calls ``/auth/me``. It runs the same live gate as the
    reads, so a revoked or expired link redirects the visitor out.
    """
    return {"ok": True}
