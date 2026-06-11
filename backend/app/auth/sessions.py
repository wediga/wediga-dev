"""Session configuration.

Sessions use Starlette's ``SessionMiddleware``, which signs a cookie with
itsdangerous and keeps no server-side state. The secret comes from
``SESSION_SECRET``. The admin session marker is ``request.session["admin"]``
and the recruiter session marker is ``request.session["recruiter"]``, which
holds the id of the redeemed link. Both markers share the one signed cookie
but are independent keys, so a recruiter session never carries the admin
marker and cannot reach an admin route.
"""

import logging
import os
import secrets

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI

logger = logging.getLogger("uvicorn.error")

SESSION_COOKIE_NAME = "wediga_session"

# Session key for the admin marker.
ADMIN_SESSION_KEY = "admin"

# Session key for the recruiter marker; holds the id of the redeemed link.
RECRUITER_SESSION_KEY = "recruiter"


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret
    # No predictable default ever ships: when SESSION_SECRET is unset we mint
    # a random per-process secret. Local startup keeps working, a missing
    # secret in production only invalidates sessions across restarts instead
    # of running with a value that sits in the repository. The fallback is
    # logged loudly so a misconfigured production is visible in the logs and
    # does not silently sign sessions with a throwaway secret.
    logger.warning(
        "SESSION_SECRET is not set; using a random per-process secret. "
        "Sessions will not survive a restart. Set SESSION_SECRET in production."
    )
    return secrets.token_urlsafe(32)


def _cookie_secure() -> bool:
    # The cookie is Secure by default, so it only travels over https behind
    # Caddy in production. Local development over http://localhost sets
    # COOKIE_SECURE=false so the session cookie round-trips.
    return os.environ.get("COOKIE_SECURE", "true").lower() != "false"


def add_session_middleware(app: FastAPI) -> None:
    """Attach the signed-cookie session middleware to the application."""
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_secret(),
        session_cookie=SESSION_COOKIE_NAME,
        https_only=_cookie_secure(),
        same_site="lax",
    )
