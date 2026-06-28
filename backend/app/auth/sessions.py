"""Session configuration.

Starlette's ``SessionMiddleware`` signs one cookie with itsdangerous and keeps
no server-side state. The admin marker is ``session["admin"]`` and the
recruiter marker is ``session["recruiter"]`` (the id of the redeemed link).
They are independent keys in the one cookie, so a recruiter session never
carries the admin marker and cannot reach an admin route.
"""

import logging
import os
import secrets

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI

logger = logging.getLogger("uvicorn.error")

SESSION_COOKIE_NAME = "wediga_session"

ADMIN_SESSION_KEY = "admin"

# Holds the id of the redeemed link.
RECRUITER_SESSION_KEY = "recruiter"

# Set after a correct password when the second factor is active. It carries no
# admin rights on its own and is cleared once the TOTP step promotes the session
# to a full admin session.
PENDING_2FA_SESSION_KEY = "pending_2fa"


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret
    # No predictable default ever ships. An unset SESSION_SECRET mints a random
    # per-process secret, so local startup works and a missing secret in
    # production only drops sessions across restarts rather than signing with a
    # value committed to the repository. The fallback is logged loudly so a
    # misconfigured production shows up.
    logger.warning(
        "SESSION_SECRET is not set; using a random per-process secret. "
        "Sessions will not survive a restart. Set SESSION_SECRET in production."
    )
    return secrets.token_urlsafe(32)


def _cookie_secure() -> bool:
    # Secure by default, so the cookie only travels over https behind Caddy.
    # Local development over http://localhost sets COOKIE_SECURE=false so the
    # cookie round-trips.
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
