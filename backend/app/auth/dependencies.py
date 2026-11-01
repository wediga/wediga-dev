"""Auth dependencies for protecting routes.

Admin and recruiter are separate parts of the same session. An admin session
never grants recruiter access implicitly and a recruiter session never grants
admin access: each dependency checks only its own part, so a shared recruiter
link can never reach an admin route.

Until the password login is removed, an admin is either the old admin login
or the admin role from the login through authentik. That login counts for
eight hours after it happened, then the visitor goes back to authentik.
"""

from fastapi import HTTPException, Request, status

from app.auth.oidc_router import ADMIN_ROLE, HUB_ROLE
from app.auth.sessions import current


def oidc_roles(request: Request) -> tuple[str, ...]:
    """Return the roles of the login through authentik, none after its
    lifetime, so authentik is asked again and reads the groups afresh."""
    state = current(request)

    return () if state is None else state.roles


def is_admin(request: Request) -> bool:
    """True for the old admin login or the admin role from authentik."""
    state = current(request)

    return state is not None and (state.legacy_admin or ADMIN_ROLE in state.roles)


def require_admin(request: Request) -> None:
    """Reject the request unless an admin session is present.

    A login through authentik without the admin role gets 403, so the admin
    area can tell it apart from no login (401) and does not send it back to
    authentik, which would return it at once.
    """
    if is_admin(request):
        return

    if oidc_roles(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin authentication required",
    )


def require_login(request: Request) -> None:
    """Pass an admin or anyone with a role from authentik, for routes every
    logged in visitor needs, such as fetching the CSRF token to log out."""
    if not (is_admin(request) or oidc_roles(request)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )


def require_hub(request: Request) -> int:
    """Pass a login through authentik with the hub role and return the
    account's ID in authentik."""
    state = current(request)

    if state is None or HUB_ROLE not in state.roles or state.authentik_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hub authentication required",
        )

    return state.authentik_user_id


def require_recruiter_or_admin(request: Request) -> None:
    """Pass a recruiter or an admin session, since the admin previews the
    recruiter pages. Neither part present is a 401.
    """
    state = current(request)

    if is_admin(request) or (state is not None and state.recruiter_link_id):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Recruiter or admin authentication required",
    )
