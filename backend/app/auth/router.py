"""Authentication routes: login, the TOTP second factor, logout and the
current-session check.

The handlers are plain ``def`` functions, so FastAPI runs their database queries
in its threadpool and the backend keeps one synchronous session helper.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.auth import sessions, totp
from app.auth.csrf import csrf_token, require_csrf
from app.auth.dependencies import require_admin, require_login
from app.auth.models import Admin, LegacyAdminLogin
from app.auth.passwords import verify_password
from app.auth.ratelimit import client_ip, login_limiter, totp_limiter
from app.db.connection import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(max_length=1024)


class CodeRequest(BaseModel):
    code: str = Field(max_length=16)


def _start_session(request: Request, second_factor_done: bool) -> None:
    """Replace any prior session with a new one holding only the old admin
    login, done or waiting for the second factor.

    The new session drops a pending login and any recruiter part and comes
    with a new token and CSRF token, so nothing survives the factor
    transition.
    """
    session_id = sessions.start(request)

    with get_session() as session:
        session.add(
            LegacyAdminLogin(
                session_id=session_id, second_factor_done=second_factor_done
            )
        )
        session.commit()


def _decrypt_secret_or_500(stored: str) -> str:
    """Decrypt a stored secret or raise a 500 for a key misconfiguration.

    A missing key or an unreadable secret is a server-side problem, not a wrong
    code, so it surfaces as a 500 without leaking detail rather than as an
    authentication failure.
    """
    try:
        return totp.decrypt_secret(stored)
    except totp.TotpKeyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Second factor is unavailable",
        ) from None


@router.post("/login")
def login(request: Request, body: LoginRequest) -> dict[str, bool]:
    """Validate the password and either start a session or demand the code.

    The per-IP rate limit returns 429 before the password is checked, so the
    argon2 verify cannot be used as a timing or load amplifier. With the second
    factor enabled a correct password only starts a login waiting for it and
    grants no admin rights until the TOTP step succeeds.
    """
    ip = client_ip(request)
    if not login_limiter.hit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, try again later",
        )

    with get_session() as session:
        admin: Admin | None = session.scalar(select(Admin))

    if admin is None or not verify_password(admin.password_hash, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # A correct password clears the counter, so earlier mistyped attempts
    # never lock out a legitimate admin.
    login_limiter.reset(ip)

    # The password alone grants no admin rights when the second factor is
    # active; only the step below promotes the login.
    _start_session(request, second_factor_done=not admin.totp_enabled)

    return {"ok": True, "totp_required": admin.totp_enabled}


@router.post("/login/totp")
def login_totp(request: Request, body: CodeRequest) -> dict[str, bool]:
    """Verify the TOTP code for a pending login and issue the admin session.

    Without a login waiting for it there is nothing to verify, so the step
    cannot mint an admin session on its own. A second per-IP limiter caps online
    guessing of the six-digit code.
    """
    state = sessions.current(request)

    if state is None or not state.pending_second_factor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No pending second factor",
        )

    ip = client_ip(request)
    if not totp_limiter.hit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many code attempts, try again later",
        )

    with get_session() as session:
        admin: Admin | None = session.scalar(select(Admin))

    if admin is None or not admin.totp_enabled or not admin.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Second factor is not active",
        )

    secret = _decrypt_secret_or_500(admin.totp_secret)

    # A TOTP code stays valid for its whole time window, so it could in principle
    # be replayed within that window. No used-code tracking is kept: one admin
    # over https with the per-IP code limit leaves a narrow window, and a lost
    # device is handled by resetting the factor on the server, so the extra state
    # would not pay for itself here.
    if not totp.verify_code(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code",
        )

    totp_limiter.reset(ip)
    _start_session(request, second_factor_done=True)
    return {"ok": True}


@router.post("/logout")
def logout(request: Request) -> dict[str, bool]:
    """End the session."""
    sessions.end(request)
    return {"ok": True}


@router.get("/me", dependencies=[Depends(require_admin)])
def me() -> dict[str, bool]:
    """Return success when an admin session is active."""
    return {"admin": True}


@router.get("/csrf", dependencies=[Depends(require_login)])
def csrf(request: Request) -> dict[str, str | None]:
    """Return the session CSRF token to send on writes. Every logged in
    visitor gets it, since logging out is a write as well."""
    return {"csrf_token": csrf_token(request)}


@router.get("/totp/status", dependencies=[Depends(require_admin)])
def totp_status() -> dict[str, bool]:
    """Report whether the second factor is active for the admin."""
    with get_session() as session:
        admin: Admin | None = session.scalar(select(Admin))

    return {"enabled": admin is not None and admin.totp_enabled}


@router.post(
    "/totp/setup",
    dependencies=[Depends(require_admin), Depends(require_csrf)],
)
def totp_setup() -> dict[str, str]:
    """Generate a fresh secret, store it encrypted and return the setup data.

    Setup is refused once the factor is active, so a stray call cannot silently
    disable a working second factor. Rotating the secret means resetting the
    factor on the server first, which matches the deliberate no-reset-endpoint
    decision. The plaintext secret is returned once for manual entry alongside
    the QR code and is never persisted in the clear.
    """
    with get_session() as session:
        admin: Admin | None = session.scalar(select(Admin))

    if admin is not None and admin.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Second factor is already active",
        )

    secret = totp.generate_secret()
    try:
        encrypted = totp.encrypt_secret(secret)
    except totp.TotpKeyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Second factor is unavailable",
        ) from None

    with get_session() as session:
        session.execute(update(Admin).values(totp_secret=encrypted, totp_enabled=False))
        session.commit()

    uri = totp.provisioning_uri(secret)
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_svg": totp.qr_svg_data_url(uri),
    }


@router.post(
    "/totp/confirm",
    dependencies=[Depends(require_admin), Depends(require_csrf)],
)
def totp_confirm(request: Request, body: CodeRequest) -> dict[str, bool]:
    """Enable the second factor once a code proves the secret was stored.

    The confirmation shares the code rate limiter, so a brute-force of the
    confirm step is capped just like the login step.
    """
    ip = client_ip(request)
    if not totp_limiter.hit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many code attempts, try again later",
        )

    with get_session() as session:
        admin: Admin | None = session.scalar(select(Admin))

    if admin is None or not admin.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run setup before confirming",
        )

    secret = _decrypt_secret_or_500(admin.totp_secret)

    if not totp.verify_code(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code",
        )

    totp_limiter.reset(ip)

    with get_session() as session:
        session.execute(update(Admin).values(totp_enabled=True))
        session.commit()

    return {"ok": True, "enabled": True}
