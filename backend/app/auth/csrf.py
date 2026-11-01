"""CSRF protection for write endpoints.

The synchronizer-token pattern: every session carries a random token, minted
anew with each login, which the admin fetches via ``GET /auth/csrf``. Every
write endpoint requires the token in the ``X-CSRF-Token`` header and compares
it against the session value in constant time. This sits on top of the
``SameSite=lax`` cookie and the forced custom header, both of which already
block the classic cross-site form post.
"""

import hmac

from fastapi import HTTPException, Request, status

from app.auth.sessions import current

# Header the client must send on writes.
CSRF_HEADER_NAME = "X-CSRF-Token"


def csrf_token(request: Request) -> str | None:
    """Return the CSRF token of the session, or ``None`` without one."""
    state = current(request)

    return None if state is None else state.csrf_token


def require_csrf(request: Request) -> None:
    """Reject the request unless the header token matches the session token.

    A missing session, a missing header or a mismatch all yield 403.
    The comparison is constant time to avoid leaking the token byte by byte.
    """
    expected = csrf_token(request)
    provided = request.headers.get(CSRF_HEADER_NAME)

    if not expected or not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token",
        )
