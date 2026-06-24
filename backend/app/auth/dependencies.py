"""Auth dependencies for protecting routes.

Admin and recruiter are two separate session markers in the same signed
cookie. An admin session never grants recruiter access implicitly and a
recruiter session never grants admin access: each dependency checks only its
own key, so a shared recruiter link can never reach an admin route.
"""

from fastapi import HTTPException, Request, status

from app.auth.sessions import ADMIN_SESSION_KEY, RECRUITER_SESSION_KEY


def require_admin(request: Request) -> None:
    """Reject the request with 401 unless an admin session is present."""
    if not request.session.get(ADMIN_SESSION_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )


def require_recruiter_or_admin(request: Request) -> None:
    """Pass a recruiter or an admin session, since the admin previews the
    recruiter pages. Neither marker present is a 401.
    """
    if not (
        request.session.get(RECRUITER_SESSION_KEY)
        or request.session.get(ADMIN_SESSION_KEY)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Recruiter or admin authentication required",
        )
