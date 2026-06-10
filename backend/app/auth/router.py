"""Authentication routes: login, logout and the current-session check.

The handlers are plain ``def`` functions, so FastAPI runs their small SQLite
queries in its threadpool. That keeps a single synchronous connection helper
across the whole backend instead of a second async layer for one query.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth.dependencies import require_admin
from app.auth.passwords import verify_password
from app.auth.sessions import ADMIN_SESSION_KEY
from app.db.connection import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(request: Request, body: LoginRequest) -> dict[str, bool]:
    """Validate the password against the admin hash and start a session."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM admin WHERE id = 1"
        ).fetchone()

    if row is None or not verify_password(row["password_hash"], body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    request.session[ADMIN_SESSION_KEY] = True
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
