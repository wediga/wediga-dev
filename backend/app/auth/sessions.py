"""Sessions kept on the server.

The cookie holds only a random token. ``access.session`` keeps its SHA-256
together with the CSRF token, and every part of a session (the login through
authentik, a login under way, the old admin login and a redeemed recruiter
link) is a row of its own that goes away with it. A deleted session stops
working with the very next request, so ending every session is one ``DELETE``.

A visitor without a login gets no row. One is made when a login starts or a
recruiter link is redeemed, and every login gives the session a new token and
a new CSRF token, so a token known from before (session fixation) stops
working.

A session ends after a while without a request. Each part also has its own
lifetime from the moment it began. Expired rows count as gone at once and are
deleted by the hourly clean-up.
"""

import asyncio
import hashlib
import logging
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import FastAPI, Request
from sqlalchemy import delete, select

from app.auth.models import (
    Account,
    AuthentikLogin,
    AuthentikLoginRole,
    BrowserSession,
    LegacyAdminLogin,
    LoginFlow,
    Role,
)
from app.db.connection import get_session, now
from app.recruiter.models import RecruiterAccess

logger = logging.getLogger("uvicorn.error")

SESSION_COOKIE_NAME = "wediga_session"

IDLE_TIMEOUT = timedelta(hours=2)
AUTHENTIK_LOGIN_LIFETIME = timedelta(hours=8)
RECRUITER_ACCESS_LIFETIME = timedelta(days=7)
# A login that is not finished within this time has to start over.
LOGIN_FLOW_LIFETIME = timedelta(minutes=10)

# The browser keeps the cookie as long as the longest part lasts. Whether the
# session behind it still counts is decided here on the server.
COOKIE_MAX_AGE_SECONDS = int(RECRUITER_ACCESS_LIFETIME.total_seconds())
CLEANUP_INTERVAL_SECONDS = 60 * 60
# Long enough for a URL-safe random value well above 128 bits.
TOKEN_BYTES = 32
MAX_USER_AGENT_LENGTH = 512

# Each part with the moment it began and how long it lasts from then.
_PART_LIFETIMES = (
    (AuthentikLogin, AuthentikLogin.logged_in_at, AUTHENTIK_LOGIN_LIFETIME),
    (LoginFlow, LoginFlow.started_at, LOGIN_FLOW_LIFETIME),
    (RecruiterAccess, RecruiterAccess.redeemed_at, RECRUITER_ACCESS_LIFETIME),
)

# Names on ``request.state``: the session as loaded for this request, a token
# to send as the new cookie and the order to remove the cookie.
_LOADED = "wediga_session"
_NEW_TOKEN = "wediga_session_new_token"
_CLEAR = "wediga_session_clear"


@dataclass(frozen=True)
class SessionState:
    """What a request may do, read once from the session and its parts."""

    id: uuid.UUID
    csrf_token: str
    authentik_user_id: int | None = None
    # Empty without a login through authentik or after its lifetime.
    roles: tuple[str, ...] = ()
    legacy_admin: bool = False
    pending_second_factor: bool = False
    recruiter_link_id: uuid.UUID | None = None


def hash_token(token: str) -> bytes:
    """Return what the database keeps of a session token."""
    return hashlib.sha256(token.encode()).digest()


def _random() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _load(token: str) -> SessionState | None:
    moment = now()

    with get_session() as db:
        row = db.scalar(
            select(BrowserSession).where(BrowserSession.token_hash == hash_token(token))
        )

        if row is None or row.last_seen_at <= moment - IDLE_TIMEOUT:
            return None

        row.last_seen_at = moment
        login = db.execute(
            select(AuthentikLogin.id, Account.authentik_user_id)
            .join(Account, Account.id == AuthentikLogin.account_id)
            .where(
                AuthentikLogin.session_id == row.id,
                AuthentikLogin.logged_in_at > moment - AUTHENTIK_LOGIN_LIFETIME,
            )
        ).one_or_none()
        roles = (
            ()
            if login is None
            else tuple(
                db.scalars(
                    select(Role.key)
                    .join(AuthentikLoginRole, AuthentikLoginRole.role_id == Role.id)
                    .where(AuthentikLoginRole.authentik_login_id == login.id)
                    .order_by(Role.key)
                )
            )
        )
        second_factor_done = db.scalar(
            select(LegacyAdminLogin.second_factor_done).where(
                LegacyAdminLogin.session_id == row.id
            )
        )
        recruiter_link_id = db.scalar(
            select(RecruiterAccess.recruiter_link_id).where(
                RecruiterAccess.session_id == row.id,
                RecruiterAccess.redeemed_at > moment - RECRUITER_ACCESS_LIFETIME,
            )
        )
        state = SessionState(
            id=row.id,
            csrf_token=row.csrf_token,
            authentik_user_id=None if login is None else login.authentik_user_id,
            roles=roles,
            legacy_admin=second_factor_done is True,
            pending_second_factor=second_factor_done is False,
            recruiter_link_id=recruiter_link_id,
        )
        db.commit()

    return state


def current(request: Request) -> SessionState | None:
    """Return the session of the request, or ``None``. It is read from the
    database once per request. A cookie without a valid session is removed."""
    if hasattr(request.state, _LOADED):
        return getattr(request.state, _LOADED)

    token = getattr(request.state, _NEW_TOKEN, None) or request.cookies.get(
        SESSION_COOKIE_NAME
    )
    state = None if token is None else _load(token)

    if token is not None and state is None:
        setattr(request.state, _CLEAR, True)

    setattr(request.state, _LOADED, state)

    return state


def _forget(request: Request) -> None:
    """Read the session again the next time it is asked for."""
    if hasattr(request.state, _LOADED):
        delattr(request.state, _LOADED)


def renew(request: Request) -> uuid.UUID:
    """Give the session a new token and a new CSRF token and return its ID.

    Without a session a new one is made. Its parts are kept.
    """
    token = _random()
    known = current(request)
    moment = now()

    with get_session() as db:
        row = None if known is None else db.get(BrowserSession, known.id)

        if row is None:
            user_agent = request.headers.get("user-agent")
            row = BrowserSession(
                token_hash=hash_token(token),
                csrf_token=_random(),
                created_at=moment,
                last_seen_at=moment,
                user_agent=user_agent and user_agent[:MAX_USER_AGENT_LENGTH],
            )
            db.add(row)
        else:
            row.token_hash = hash_token(token)
            row.csrf_token = _random()

        db.commit()
        session_id = row.id

    setattr(request.state, _NEW_TOKEN, token)
    _forget(request)

    return session_id


def ensure(request: Request) -> uuid.UUID:
    """Return the ID of the session, made first if there is none. The token
    stays, so a link from another site cannot swap it."""
    known = current(request)

    return renew(request) if known is None else known.id


def end(request: Request) -> None:
    """Delete the session with all its parts and remove the cookie."""
    known = current(request)

    if known is not None:
        with get_session() as db:
            db.execute(delete(BrowserSession).where(BrowserSession.id == known.id))
            db.commit()

    if hasattr(request.state, _NEW_TOKEN):
        delattr(request.state, _NEW_TOKEN)

    setattr(request.state, _CLEAR, True)
    setattr(request.state, _LOADED, None)


def start(request: Request) -> uuid.UUID:
    """Replace the session with a new one without any part and return its ID."""
    end(request)

    return renew(request)


def drop_parts(
    request: Request,
    *models: type[AuthentikLogin | LoginFlow | LegacyAdminLogin | RecruiterAccess],
) -> None:
    """Remove the given parts from the session, keep the session itself."""
    known = current(request)

    if known is None:
        return

    with get_session() as db:
        for model in models:
            db.execute(delete(model).where(model.session_id == known.id))

        db.commit()

    _forget(request)


def delete_expired() -> None:
    """Delete every session and every part past its lifetime."""
    moment = now()

    with get_session() as db:
        db.execute(
            delete(BrowserSession).where(
                BrowserSession.last_seen_at <= moment - IDLE_TIMEOUT
            )
        )

        for model, began, lifetime in _PART_LIFETIMES:
            db.execute(delete(model).where(began <= moment - lifetime))

        db.commit()


async def _cleanup_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(delete_expired)
        except Exception:
            logger.warning("deleting expired sessions failed", exc_info=True)

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


def start_cleanup() -> asyncio.Task:
    """Delete expired sessions now and then every hour, in the background."""
    return asyncio.create_task(_cleanup_loop())


def _cookie_secure() -> bool:
    # Secure by default, so the cookie only travels over https behind Caddy.
    # Local development over http://localhost sets COOKIE_SECURE=false so the
    # cookie round-trips.
    return os.environ.get("COOKIE_SECURE", "true").lower() != "false"


def add_session_middleware(app: FastAPI) -> None:
    """Set or remove the cookie after a request that changed it."""
    secure = _cookie_secure()

    @app.middleware("http")
    async def session_cookie(request: Request, call_next):
        response = await call_next(request)
        token = getattr(request.state, _NEW_TOKEN, None)

        if token is not None:
            response.set_cookie(
                SESSION_COOKIE_NAME,
                token,
                max_age=COOKIE_MAX_AGE_SECONDS,
                secure=secure,
                httponly=True,
                samesite="lax",
            )
        elif getattr(request.state, _CLEAR, False):
            response.delete_cookie(
                SESSION_COOKIE_NAME, secure=secure, httponly=True, samesite="lax"
            )

        return response
