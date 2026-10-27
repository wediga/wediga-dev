"""Routes of the login through authentik: start, callback and logout.

All three answer 404 while ``OIDC_ENABLED`` is off. The login keeps its own
key in the session next to the recruiter key, so logging in or out through
authentik never touches a recruiter session. The old admin marker and the
CSRF token are dropped on both, so no right or token of an earlier login
carries over.
"""

import hmac
import logging
import re
import secrets
import time
from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.auth import oidc
from app.auth.csrf import CSRF_SESSION_KEY, issue_csrf_token, require_csrf
from app.auth.oidc_settings import OidcSettings
from app.auth.sessions import (
    ADMIN_SESSION_KEY,
    OIDC_FLOW_SESSION_KEY,
    OIDC_SESSION_KEY,
    PENDING_2FA_SESSION_KEY,
)

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
ADMIN_HOME = "/admin"
HUB_HOME = "/hub"
NO_ACCESS_PATH = "/no-access"

# A login that is not finished within this time has to start over.
FLOW_MAX_AGE_SECONDS = 600
# Long enough for a URL-safe random value well above 128 bits.
RANDOM_BYTES = 32
# Only a plain path on this site is a valid target after the login: it starts
# with one slash, never two, and has no backslash, colon, whitespace or
# fragment, so no browser can read it as another host.
SAFE_TARGET = re.compile(r"/(?!/)[A-Za-z0-9\-._~/?=&%]*")
MAX_TARGET_LENGTH = 512


class LoginFlow(TypedDict):
    """A login under way, kept in the session until the callback."""

    state: str
    nonce: str
    verifier: str
    target: str | None
    started: int


class OidcLogin(TypedDict):
    """A finished login. Holds no token from authentik."""

    roles: list[str]
    login_at: int


def require_oidc(request: Request) -> OidcSettings:
    """Hide the routes behind a 404 while the login is switched off.

    Before the startup has run there are no settings, which counts as off.
    """
    settings = getattr(request.app.state, "oidc", None)

    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return settings


Settings = Annotated[OidcSettings, Depends(require_oidc)]

# On the router, so the switch is checked before any route's own dependency
# (such as the CSRF check) and a switched off login never reveals itself.
router = APIRouter(
    prefix="/auth/oidc", tags=["auth"], dependencies=[Depends(require_oidc)]
)


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


def _drop_login_state(request: Request) -> None:
    """Remove every login and its CSRF token, keep a recruiter session."""
    for key in (
        ADMIN_SESSION_KEY,
        PENDING_2FA_SESSION_KEY,
        CSRF_SESSION_KEY,
        OIDC_SESSION_KEY,
        OIDC_FLOW_SESSION_KEY,
    ):
        request.session.pop(key, None)


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

    State, nonce and PKCE verifier stay in the signed session until the
    callback. A target outside this site is dropped, not refused, so a bad
    link still leads to a login.
    """
    metadata = _metadata_or_502(settings)
    flow = LoginFlow(
        state=secrets.token_urlsafe(RANDOM_BYTES),
        nonce=secrets.token_urlsafe(RANDOM_BYTES),
        verifier=secrets.token_urlsafe(RANDOM_BYTES),
        target=safe_target(target),
        started=int(time.time()),
    )
    request.session[OIDC_FLOW_SESSION_KEY] = flow
    url = oidc.authorization_url(
        settings, metadata, flow["state"], flow["nonce"], flow["verifier"]
    )

    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/callback")
def callback(
    request: Request,
    settings: Settings,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Finish the login: check state, trade the code, validate the ID token and
    turn the groups into roles.

    The flow is removed before any check, so a state is good for one attempt
    only. Without a matching group the visitor gets no session and lands on
    the no-access page.
    """
    flow: LoginFlow | None = request.session.pop(OIDC_FLOW_SESSION_KEY, None)

    if (
        flow is None
        or not code
        or not state
        or int(time.time()) - flow["started"] > FLOW_MAX_AGE_SECONDS
        or not hmac.compare_digest(flow["state"], state)
    ):
        raise _invalid_login()

    metadata = _metadata_or_502(settings)

    try:
        token = oidc.exchange_code(settings, metadata, code, flow["verifier"])
        claims = oidc.validate_id_token(settings, metadata, token, flow["nonce"])
    except oidc.OidcProviderError:
        logger.warning("authentik token exchange failed", exc_info=True)

        raise _provider_unavailable() from None
    except oidc.OidcTokenError:
        logger.warning("authentik ID token rejected", exc_info=True)

        raise _invalid_login() from None

    roles = roles_for(claims.get("groups"))
    _drop_login_state(request)

    if not roles:
        return RedirectResponse(NO_ACCESS_PATH, status_code=status.HTTP_303_SEE_OTHER)

    request.session[OIDC_SESSION_KEY] = OidcLogin(
        roles=roles, login_at=int(time.time())
    )
    # A fresh token, so none from before the login stays valid.
    issue_csrf_token(request)
    home = ADMIN_HOME if ADMIN_ROLE in roles else HUB_HOME

    return RedirectResponse(
        flow["target"] or home, status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request, settings: Settings) -> dict[str, str]:
    """End the login here and return the authentik URL that ends it there.

    The local logout always happens. If authentik cannot be reached, the
    browser goes to the start page instead.
    """
    _drop_login_state(request)

    try:
        url = oidc.end_session_url(settings, oidc.load_metadata(settings))
    except oidc.OidcProviderError:
        logger.warning("authentik end-session URL unavailable", exc_info=True)

        return {"redirect": START_PAGE}

    return {"redirect": url}
