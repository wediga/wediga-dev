"""In-memory rate limiting for the admin login.

The login is the one brute-force surface, so it gets a small per-IP limiter.
wediga.dev runs a single backend process, so an in-memory fixed-window
counter is enough and avoids pulling in a dependency for one endpoint. The
counter keys on the client IP and resets once its window elapses, and a stale
window is pruned on access so the dictionary cannot grow without bound under
normal traffic.

The client IP is read from ``X-Forwarded-For`` because the browser reaches the
backend only through Caddy and the Next.js BFF, both of which sit in front. The
backend is not publicly reachable, so the forwarded header is trusted as set by
that proxy chain. When the header is absent (local development without a proxy)
the limiter falls back to the direct peer address.
"""

import time
from threading import Lock


def client_ip(request) -> str:
    """Return the trusted client IP for rate-limiting and tracking.

    Caddy appends the real peer as the last ``X-Forwarded-For`` entry, while
    any values a client injects sit to its left, so the rightmost entry is the
    address the trusted proxy observed. Reading the leftmost entry instead
    would let a client forge a fresh value per request and so escape the rate
    limit, which is why the rightmost entry is used here. The Next.js BFF
    forwards the header without adding a hop, so exactly one proxy (Caddy)
    appends. Without the header the direct peer is used for local development.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """A fixed-window per-key counter.

    ``max_attempts`` requests are allowed per ``window_seconds``. The window
    starts at the first request for a key and the count resets once it elapses.
    """

    def __init__(
        self, max_attempts: int, window_seconds: float, max_keys: int = 10000
    ) -> None:
        self._max = max_attempts
        self._window = window_seconds
        self._max_keys = max_keys
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def hit(self, key: str) -> bool:
        """Record an attempt for ``key`` and return ``True`` if it is allowed."""
        nowt = time.monotonic()
        with self._lock:
            # Bound memory: once the table grows past the cap, drop every key
            # whose window has fully elapsed. What remains are only the keys
            # active inside the current window, so the table cannot grow
            # without bound under a spread of distinct addresses.
            if len(self._hits) > self._max_keys:
                self._hits = {
                    k: v
                    for k, v in self._hits.items()
                    if nowt - v[0] < self._window
                }
            window_start, count = self._hits.get(key, (nowt, 0))
            if nowt - window_start >= self._window:
                window_start, count = nowt, 0
            count += 1
            self._hits[key] = (window_start, count)
            return count <= self._max

    def reset(self, key: str) -> None:
        """Clear the counter for ``key`` (used after a successful login)."""
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        """Drop all counters. Used to isolate the limiter between tests."""
        with self._lock:
            self._hits.clear()


# A single shared limiter for the login: ten attempts per five minutes per IP.
# With argon2 at roughly 50 ms per verify this leaves brute force hopeless
# without locking out a person who simply mistypes the password a few times.
login_limiter = RateLimiter(max_attempts=10, window_seconds=300)
