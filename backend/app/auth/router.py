"""Authentication routes: login, the TOTP second factor, logout and the
current-session check.

The handlers are plain ``def`` functions, so FastAPI runs their SQLite queries
in its threadpool and the backend keeps one synchronous connection helper.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.csrf import issue_csrf_token, require_csrf
from app.auth.dependencies import require_admin
from app.auth.passwords import verify_password
from app.auth.ratelimit import client_ip, login_limiter, totp_limiter
from app.auth.sessions import ADMIN_SESSION_KEY, PENDING_2FA_SESSION_KEY
from app.auth import totp
from app.db.connection import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(max_length=1024)


class CodeRequest(BaseModel):
    code: str = Field(max_length=16)


def _start_admin_session(request: Request) -> None:
    """Drop any prior session state and issue a fresh admin session.

    Clearing first removes the ``pending_2fa`` marker and any recruiter state,
    so the elevated session carries only the admin marker and a new CSRF token.
    The signed cookie is rewritten on this change, so no stale marker survives
    the factor transition.
    """
    request.session.clear()
    request.session[ADMIN_SESSION_KEY] = True
    # Mint the CSRF token now so the admin can read it right after login.
    issue_csrf_token(request)


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
        )


@router.post("/login")
def login(request: Request, body: LoginRequest) -> dict[str, bool]:
    """Validate the password and either start a session or demand the code.

    The per-IP rate limit returns 429 before the password is checked, so the
    argon2 verify cannot be used as a timing or load amplifier. With the second
    factor enabled a correct password only sets ``pending_2fa`` and grants no
    admin rights until the TOTP step succeeds.
    """
    ip = client_ip(request)
    if not login_limiter.hit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, try again later",
        )

    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash, totp_enabled FROM admin WHERE id = 1"
        ).fetchone()

    if row is None or not verify_password(row["password_hash"], body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # A correct password clears the counter, so earlier mistyped attempts
    # never lock out a legitimate admin.
    login_limiter.reset(ip)

    if row["totp_enabled"]:
        # The password alone grants no admin rights; only the second factor
        # below promotes this to an admin session.
        request.session.clear()
        request.session[PENDING_2FA_SESSION_KEY] = True
        return {"ok": True, "totp_required": True}

    _start_admin_session(request)
    return {"ok": True, "totp_required": False}


@router.post("/login/totp")
def login_totp(request: Request, body: CodeRequest) -> dict[str, bool]:
    """Verify the TOTP code for a pending login and issue the admin session.

    Without a ``pending_2fa`` marker there is nothing to verify, so the step
    cannot mint an admin session on its own. A second per-IP limiter caps online
    guessing of the six-digit code.
    """
    if not request.session.get(PENDING_2FA_SESSION_KEY):
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

    with get_connection() as conn:
        row = conn.execute(
            "SELECT totp_secret, totp_enabled FROM admin WHERE id = 1"
        ).fetchone()

    if row is None or not row["totp_enabled"] or not row["totp_secret"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Second factor is not active",
        )

    secret = _decrypt_secret_or_500(row["totp_secret"])

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
    _start_admin_session(request)
    return {"ok": True}


@router.post("/logout")
def logout(request: Request) -> dict[str, bool]:
    """Clear the session."""
    request.session.clear()
    return {"ok": True}


@router.get("/me", dependencies=[Depends(require_admin)])
def me() -> dict[str, bool]:
    """Return success when an admin session is active."""
    return {"admin": True}


@router.get("/csrf", dependencies=[Depends(require_admin)])
def csrf(request: Request) -> dict[str, str]:
    """Return the session CSRF token for the admin to send on writes."""
    return {"csrf_token": issue_csrf_token(request)}


@router.get("/totp/status", dependencies=[Depends(require_admin)])
def totp_status() -> dict[str, bool]:
    """Report whether the second factor is active for the admin."""
    with get_connection() as conn:
        row = conn.execute("SELECT totp_enabled FROM admin WHERE id = 1").fetchone()
    return {"enabled": bool(row and row["totp_enabled"])}


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
    with get_connection() as conn:
        active = conn.execute(
            "SELECT totp_enabled FROM admin WHERE id = 1"
        ).fetchone()
    if active and active["totp_enabled"]:
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
        )

    with get_connection() as conn:
        conn.execute(
            "UPDATE admin SET totp_secret = ?, totp_enabled = 0 WHERE id = 1",
            (encrypted,),
        )
        conn.commit()

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

    with get_connection() as conn:
        row = conn.execute(
            "SELECT totp_secret FROM admin WHERE id = 1"
        ).fetchone()

    if row is None or not row["totp_secret"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run setup before confirming",
        )

    secret = _decrypt_secret_or_500(row["totp_secret"])

    if not totp.verify_code(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code",
        )

    totp_limiter.reset(ip)
    with get_connection() as conn:
        conn.execute("UPDATE admin SET totp_enabled = 1 WHERE id = 1")
        conn.commit()
    return {"ok": True, "enabled": True}
