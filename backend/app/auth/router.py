"""Authentication routes: login, logout and the current-session check.

The handlers are plain ``def`` functions, so FastAPI runs their small SQLite
queries in its threadpool. That keeps a single synchronous connection helper
across the whole backend instead of a second async layer for one query.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.csrf import issue_csrf_token
from app.auth.dependencies import require_admin
from app.auth.passwords import verify_password
from app.auth.ratelimit import client_ip, login_limiter
from app.auth.sessions import ADMIN_SESSION_KEY
from app.db.connection import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(max_length=1024)


@router.post("/login")
def login(request: Request, body: LoginRequest) -> dict[str, bool]:
    """Validate the password against the admin hash and start a session.

    A per-IP rate limit guards the brute-force surface: too many attempts in
    the window return 429 before the password is even checked, so the argon2
    verify cannot be used as a timing or load amplifier.
    """
    ip = client_ip(request)
    if not login_limiter.hit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, try again later",
        )

    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM admin WHERE id = 1"
        ).fetchone()

    if row is None or not verify_password(row["password_hash"], body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # A correct password clears the counter, so a legitimate admin is never
    # locked out by earlier mistyped attempts.
    login_limiter.reset(ip)
    request.session[ADMIN_SESSION_KEY] = True
    # Mint the CSRF token now, so the admin can read it right after login.
    issue_csrf_token(request)
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
