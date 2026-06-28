"""CSRF protection for write endpoints.

The signed session cookie is a state carrier, so the synchronizer-token
pattern fits: a random token is minted at login, stored in the session and
handed to the admin via ``GET /auth/csrf``. Every write endpoint requires the
token in the ``X-CSRF-Token`` header and compares it against the session value
in constant time. This sits on top of the ``SameSite=lax`` cookie and the
forced custom header, both of which already block the classic cross-site form
post.
"""

import hmac
import secrets

from fastapi import HTTPException, Request, status

# Session key holding the per-session CSRF token.
CSRF_SESSION_KEY = "csrf"

# Header the client must send on writes.
CSRF_HEADER_NAME = "X-CSRF-Token"


def issue_csrf_token(request: Request) -> str:
    """Return the session CSRF token, minting one if none exists yet."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def require_csrf(request: Request) -> None:
    """Reject the request unless the header token matches the session token.

    A missing session token, a missing header or a mismatch all yield 403.
    The comparison is constant time to avoid leaking the token byte by byte.
    """
    expected = request.session.get(CSRF_SESSION_KEY)
    provided = request.headers.get(CSRF_HEADER_NAME)
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token",
        )
