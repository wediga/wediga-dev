"""The recruiter read gate, enforced against the live link state.

The marker-only dependencies in ``app.auth.dependencies`` answer „is there a
session", which is enough to compose on, but a recruiter session must also
stop working the moment the admin revokes the link or it expires. This gate
therefore re-checks the link behind the session on every recruiter read and
drops a now-invalid marker, so revocation and expiry close an open session and
not only the entrance. An admin session passes without a link lookup, because
the admin previews the same pages.
"""

from fastapi import HTTPException, Request, status

from app.auth.dependencies import require_recruiter_or_admin
from app.auth.sessions import ADMIN_SESSION_KEY, RECRUITER_SESSION_KEY
from app.recruiter import repository as repo


def require_recruiter_view(request: Request) -> None:
    """Allow an admin, or a recruiter whose link is still active."""
    require_recruiter_or_admin(request)
    if request.session.get(ADMIN_SESSION_KEY):
        return
    link_id = request.session.get(RECRUITER_SESSION_KEY)
    if not repo.link_is_active(link_id):
        # Clear the stale marker so the revoked or expired link stops working.
        request.session.pop(RECRUITER_SESSION_KEY, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Recruiter link no longer valid",
        )
