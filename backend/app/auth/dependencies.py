"""Auth dependencies for protecting routes."""

from fastapi import HTTPException, Request, status

from app.auth.sessions import ADMIN_SESSION_KEY


def require_admin(request: Request) -> None:
    """Reject the request with 401 unless an admin session is present.

    The recruiter session key is deliberately not checked here; that flow is
    built in a later phase.
    """
    if not request.session.get(ADMIN_SESSION_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
