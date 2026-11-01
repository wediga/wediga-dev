"""Routes of the login through authentik: start, callback and logout.

All three answer 404 while ``OIDC_ENABLED`` is off. The login is a part of
the session next to the recruiter part, so logging in or out through
authentik never touches a recruiter session. The old admin login is dropped on
both, and the session gets a new token and CSRF token, so no right or token of
an earlier login carries over.
"""

import hmac
import logging
import re
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Row

from app.auth import oidc, sessions
from app.auth.csrf import require_csrf
from app.auth.models import (
    Account,
    AuthentikLogin,
    AuthentikLoginRole,
    LegacyAdminLogin,
    LoginFlow,
    Role,
)
from app.auth.oidc_settings import OidcSettings
from app.db.connection import get_session, now

logger = logging.getLogger("uvicorn.error")


ADMIN_ROLE = "admin"
HUB_ROLE = "hub"
ADMIN_GROUP = "wediga-admins"
FRIENDS_GROUP = "friends"
# Admins see the hub as well, without being members of the friends group.
GROUP_ROLES = {
    ADMIN_GROUP: (ADMIN_ROLE, HUB_ROLE),
    FRIENDS_GROUP: (HUB_ROLE,),
}

START_PAGE = "/"
PASSWORD_LOGIN_PAGE = "/login"
ADMIN_HOME = "/admin"
HUB_HOME = "/hub"
NO_ACCESS_PATH = "/no-access"

# Long enough for a URL-safe random value well above 128 bits.
RANDOM_BYTES = 32
# Only a plain path on this site is a valid target after the login: it starts
# with one slash, never two, and has no backslash, colon, whitespace or
# fragment, so no browser can read it as another host.
SAFE_TARGET = re.compile(r"/(?!/)[A-Za-z0-9\-._~/?=&%]*")
MAX_TARGET_LENGTH = 512
# authentik sends the account's numeric ID as "sub" (sub_mode user_id in the
# blueprint). The hub asks authentik with it which applications the account
# may use.
ACCOUNT_ID = re.compile(r"[0-9]+")


def _oidc_settings(request: Request) -> OidcSettings | None:
    """Before the startup has run there are no settings, which counts as off."""
    return getattr(request.app.state, "oidc", None)


def require_oidc(request: Request) -> OidcSettings:
    """Hide the routes behind a 404 while the login is switched off."""
    settings = _oidc_settings(request)

    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return settings


Settings = Annotated[OidcSettings, Depends(require_oidc)]

# On the router, so the switch is checked before any route's own dependency
# (such as the CSRF check) and a switched off login never reveals itself.
router = APIRouter(
    prefix="/auth/oidc", tags=["auth"], dependencies=[Depends(require_oidc)]
)
# Without the switch check, so the login page can ask whether to offer the
# login through authentik.
status_router = APIRouter(prefix="/auth/oidc", tags=["auth"])


@status_router.get("/status")
def login_status(request: Request) -> dict[str, bool]:
    """Tell whether the login through authentik is switched on."""
    return {"enabled": _oidc_settings(request) is not None}


def safe_target(value: str | None) -> str | None:
    """Return ``value`` when it is a path on this site, otherwise ``None``."""
    if value and len(value) <= MAX_TARGET_LENGTH and SAFE_TARGET.fullmatch(value):
        return value

    return None


def roles_for(groups: object) -> list[str]:
    """Map authentik groups to roles. Unknown groups give no role."""
    if not isinstance(groups, list):
        return []

    roles = {
        role
        for group in groups
        if isinstance(group, str)
        for role in GROUP_ROLES.get(group, ())
    }

    return sorted(roles)


def _drop_logins(request: Request) -> None:
    """Remove every login from the session, keep a recruiter part."""
    sessions.drop_parts(request, AuthentikLogin, LegacyAdminLogin, LoginFlow)


def _take_flow(request: Request) -> Row | None:
    """Remove the login under way from the session and return it, unless it
    is missing or too old."""
    state = sessions.current(request)

    if state is None:
        return None

    with get_session() as db:
        flow = db.execute(
            delete(LoginFlow)
            .where(LoginFlow.session_id == state.id)
            .returning(
                LoginFlow.state,
                LoginFlow.nonce,
                LoginFlow.verifier,
                LoginFlow.target,
                LoginFlow.started_at,
            )
        ).one_or_none()
        db.commit()

    if flow is None or flow.started_at <= now() - sessions.LOGIN_FLOW_LIFETIME:
        return None

    return flow


def _record_login(
    session_id: uuid.UUID, authentik_user_id: int, name: str, roles: list[str]
) -> None:
    """Store the account with its current name and the login with its roles."""
    moment = now()

    with get_session() as db:
        account_id = db.execute(
            insert(Account)
            .values(
                authentik_user_id=authentik_user_id,
                name=name,
                first_login_at=moment,
                last_login_at=moment,
            )
            .on_conflict_do_update(
                index_elements=[Account.authentik_user_id],
                set_={"name": name, "last_login_at": moment},
            )
            .returning(Account.id)
        ).scalar_one()
        db.execute(
            insert(Role)
            .values([{"key": role} for role in roles])
            .on_conflict_do_nothing()
        )
        login = AuthentikLogin(
            session_id=session_id, account_id=account_id, logged_in_at=moment
        )
        db.add(login)
        db.flush()
        db.add_all(
            AuthentikLoginRole(authentik_login_id=login.id, role_id=role_id)
            for role_id in db.scalars(select(Role.id).where(Role.key.in_(roles)))
        )
        db.commit()


def _provider_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Login provider unavailable",
    )


def _metadata_or_502(settings: OidcSettings) -> dict:
    try:
        return oidc.load_metadata(settings)
    except oidc.OidcProviderError:
        logger.warning("authentik discovery failed", exc_info=True)

        raise _provider_unavailable() from None


def _invalid_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid login response",
    )


@router.get("/login")
def login(
    request: Request,
    settings: Settings,
    target: Annotated[str | None, Query(alias="next")] = None,
) -> RedirectResponse:
    """Start a login and send the browser to authentik.

    State, nonce and PKCE verifier stay in the session until the callback.
    A target outside this site is dropped, not refused, so a bad link still
    leads to a login.
    """
    metadata = _metadata_or_502(settings)
    # No new token yet, the callback gives one once the login succeeds.
    session_id = sessions.ensure(request)
    sessions.drop_parts(request, LoginFlow)
    flow = LoginFlow(
        session_id=session_id,
        state=secrets.token_urlsafe(RANDOM_BYTES),
        nonce=secrets.token_urlsafe(RANDOM_BYTES),
        verifier=secrets.token_urlsafe(RANDOM_BYTES),
        started_at=now(),
        target=safe_target(target),
    )
    url = oidc.authorization_url(
        settings, metadata, flow.state, flow.nonce, flow.verifier
    )

    with get_session() as db:
        db.add(flow)
        db.commit()

    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/callback")
def callback(
    request: Request,
    settings: Settings,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Finish the login: check state, trade the code, validate the ID token,
    take the account ID and name and turn the groups into roles.

    The flow is removed before any check, so a state is good for one attempt
    only. Without a matching group the visitor gets no login and lands on the
    no-access page.
    """
    flow = _take_flow(request)

    if (
        flow is None
        or not code
        or not state
        or not hmac.compare_digest(flow.state, state)
    ):
        raise _invalid_login()

    metadata = _metadata_or_502(settings)

    try:
        token = oidc.exchange_code(settings, metadata, code, flow.verifier)
        claims = oidc.validate_id_token(settings, metadata, token, flow.nonce)
    except oidc.OidcProviderError:
        logger.warning("authentik token exchange failed", exc_info=True)

        raise _provider_unavailable() from None
    except oidc.OidcTokenError:
        logger.warning("authentik ID token rejected", exc_info=True)

        raise _invalid_login() from None

    sub = claims.get("sub")

    if not isinstance(sub, str) or not ACCOUNT_ID.fullmatch(sub):
        logger.warning("authentik sent no numeric account ID as sub")

        raise _invalid_login()

    name = claims.get("name")

    if not isinstance(name, str):
        logger.warning("authentik sent no name")

        raise _invalid_login()

    roles = roles_for(claims.get("groups"))
    _drop_logins(request)

    if not roles:
        return RedirectResponse(NO_ACCESS_PATH, status_code=status.HTTP_303_SEE_OTHER)

    # A new token, so none known from before the login stays valid.
    session_id = sessions.renew(request)
    _record_login(session_id, int(sub), name, roles)
    home = ADMIN_HOME if ADMIN_ROLE in roles else HUB_HOME

    return RedirectResponse(flow.target or home, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request, settings: Settings) -> dict[str, str]:
    """End the login here and return the authentik URL that ends it there.

    The local logout always happens. A session without a login through
    authentik (the password login) has nothing to end there and goes back to
    the password login. If authentik cannot be reached, the browser goes to
    the start page instead.
    """
    state = sessions.current(request)

    # Past its eight hours the login still counts here, since the session in
    # authentik may well outlast it.
    with get_session() as db:
        had_authentik_login = state is not None and bool(
            db.scalar(select(exists().where(AuthentikLogin.session_id == state.id)))
        )

    _drop_logins(request)
    sessions.renew(request)

    if not had_authentik_login:
        return {"redirect": PASSWORD_LOGIN_PAGE}

    try:
        url = oidc.end_session_url(settings, oidc.load_metadata(settings))
    except oidc.OidcProviderError:
        logger.warning("authentik end-session URL unavailable", exc_info=True)

        return {"redirect": START_PAGE}

    return {"redirect": url}
