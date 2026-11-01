"""The recruiter read gate, enforced against the live link state.

A part check answers "is there a session", but a recruiter session must also
stop working the moment the admin revokes the link or it expires. This gate
re-checks the link behind the session on every recruiter read and drops a
now-invalid recruiter part, so revocation and expiry cut live sessions, not
just new ones. An admin session passes without a link lookup, since the admin
previews the same pages.
"""

from fastapi import HTTPException, Request, status

from app.auth.dependencies import is_admin, require_recruiter_or_admin
from app.auth.sessions import current, drop_parts
from app.recruiter import repository as repo
from app.recruiter.models import RecruiterAccess


def require_recruiter_view(request: Request) -> None:
    """Allow an admin, or a recruiter whose link is still active."""
    require_recruiter_or_admin(request)

    if is_admin(request):
        return

    state = current(request)

    if state is None or not repo.link_is_active(state.recruiter_link_id):
        # Drop the stale part so the revoked or expired link stops working.
        drop_parts(request, RecruiterAccess)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Recruiter link no longer valid",
        )
