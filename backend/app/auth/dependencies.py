"""Auth dependencies for protecting routes.

Admin and recruiter are two separate session markers in the same signed
cookie. An admin session never grants recruiter access implicitly and a
recruiter session never grants admin access: each dependency checks only its
own key, so a shared recruiter link can never reach an admin route.

Until the password login is removed, an admin is either the old admin marker
or the admin role from the login through authentik. That login counts for
eight hours after it happened, then the visitor goes back to authentik.
"""

import time

from fastapi import HTTPException, Request, status

from app.auth.oidc_router import ADMIN_ROLE
from app.auth.sessions import (
    ADMIN_SESSION_KEY,
    OIDC_SESSION_KEY,
    RECRUITER_SESSION_KEY,
)

OIDC_LOGIN_LIFETIME_SECONDS = 8 * 60 * 60


def oidc_roles(request: Request) -> list[str]:
    """Return the roles of the login through authentik.

    A login older than the lifetime gives no roles and is removed from the
    session, so authentik is asked again and reads the groups afresh.
    """
    login = request.session.get(OIDC_SESSION_KEY)

    if login is None:
        return []

    if time.time() - login["login_at"] > OIDC_LOGIN_LIFETIME_SECONDS:
        request.session.pop(OIDC_SESSION_KEY)

        return []

    return login["roles"]


def is_admin(request: Request) -> bool:
    """True for the old admin marker or the admin role from authentik."""
    if request.session.get(ADMIN_SESSION_KEY):
        return True

    return ADMIN_ROLE in oidc_roles(request)


def require_admin(request: Request) -> None:
    """Reject the request with 401 unless an admin session is present."""
    if not is_admin(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )


def require_login(request: Request) -> None:
    """Pass an admin or anyone with a role from authentik, for routes every
    logged in visitor needs, such as fetching the CSRF token to log out."""
    if not (request.session.get(ADMIN_SESSION_KEY) or oidc_roles(request)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )


def require_recruiter_or_admin(request: Request) -> None:
    """Pass a recruiter or an admin session, since the admin previews the
    recruiter pages. Neither marker present is a 401.
    """
    if not (request.session.get(RECRUITER_SESSION_KEY) or is_admin(request)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Recruiter or admin authentication required",
        )
