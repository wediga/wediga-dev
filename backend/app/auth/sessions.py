"""Session configuration.

Sessions use Starlette's ``SessionMiddleware``, which signs a cookie with
itsdangerous and keeps no server-side state. The secret comes from
``SESSION_SECRET``. The admin session marker is ``request.session["admin"]``.

A recruiter session would use a separate key (``recruiter``) and is left as a
placeholder here. It is intentionally not built in this phase.
"""

import os
import secrets

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI

SESSION_COOKIE_NAME = "wediga_session"

# Session key for the admin marker.
ADMIN_SESSION_KEY = "admin"

# Reserved for a future recruiter session (Phase 4). Not used yet.
RECRUITER_SESSION_KEY = "recruiter"


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret
    # No predictable default ever ships: when SESSION_SECRET is unset we mint
    # a random per-process secret. Local startup keeps working, a missing
    # secret in production only invalidates sessions across restarts instead
    # of running with a value that sits in the repository.
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
