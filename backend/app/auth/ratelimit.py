"""Single-process fixed-window per-IP limiter for the admin login.

The client IP comes from ``X-Forwarded-For``, trusted because the backend is
reachable only through the Caddy and Next.js BFF proxy chain that sets it.
"""

import ipaddress
import time
from threading import Lock

# An IPv6 subscriber usually gets a whole /64 from their provider, so counting
# single addresses would let them rotate through it and escape every limit.
IPV6_LIMIT_PREFIX_BITS = 64


def client_ip(request) -> str:
    """Return the trusted client IP for rate-limiting and tracking.

    Use the rightmost ``X-Forwarded-For`` entry: Caddy appends the real peer
    there, while any client-injected values sit to its left. Reading the
    leftmost entry would let a client forge a fresh value per request and
    escape the limit. The BFF adds no hop, so exactly one proxy appends.
    Without the header the direct peer is used for local development.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"


def limit_key(request) -> str:
    """Return the key the rate limiters count a request under.

    An IPv4 address counts on its own, an IPv6 address counts for its whole
    /64. A value that is no address is used as it is.
    """
    ip = client_ip(request)

    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip

    if isinstance(address, ipaddress.IPv4Address):
        return ip

    return str(ipaddress.ip_network(f"{ip}/{IPV6_LIMIT_PREFIX_BITS}", strict=False))


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
            # Past the cap, drop every key whose window has fully elapsed, so
            # the table cannot grow without bound under a spread of addresses.
            if len(self._hits) > self._max_keys:
                self._hits = {
                    k: v for k, v in self._hits.items() if nowt - v[0] < self._window
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
        """Drop all counters, to isolate the limiter between tests."""
        with self._lock:
            self._hits.clear()


# Login: ten attempts per five minutes per IP. With argon2 at ~50 ms per verify
# this stops brute force without locking out a few mistyped passwords.
login_limiter = RateLimiter(max_attempts=10, window_seconds=300)

# Recruiter redeem: thirty attempts per five minutes per IP. The token carries
# 256 bits of entropy, so this only caps request floods and view-count
# inflation from one source, not guessing.
redeem_limiter = RateLimiter(max_attempts=30, window_seconds=300)

# TOTP code: five attempts per five minutes per IP. A six-digit code has a
# million-value space, so this caps online guessing on the second factor while
# leaving room for a few mistyped codes. The same limiter covers the login code
# step and the setup confirmation.
totp_limiter = RateLimiter(max_attempts=5, window_seconds=300)
