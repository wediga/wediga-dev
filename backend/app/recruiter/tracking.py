"""Data-sparse origin for the link-view tracking.

The tracking keeps when a link was opened and roughly from where, never the
full client IP. The address is first coarsened to its network prefix (a /24
for IPv4, a /48 for IPv6) so the host bits are dropped, and that prefix is
then hashed with a per-deployment salt. The stored value is therefore a stable
opaque token: two opens from the same rough network share a token so the admin
sees repeat origins, yet the value cannot be reversed to an address, and even a
leaked salt would only expose a network prefix and never a full IP. A regulator
view treats a bare truncated or unsalted-hashed IP as still identifying, which
is why both steps are applied together here. An address that cannot be parsed
is recorded as ``unknown``.

The salt comes from ``TRACKING_SALT`` when set, otherwise it falls back to the
already configured ``SESSION_SECRET`` so grouping stays stable across restarts
in any real deployment without a second secret to manage. Only when neither is
set, as in a bare local run, a random per-process salt is used, which keeps
grouping within that process and resets on restart, because tracking is not
security-critical and must never block startup.
"""

import hashlib
import ipaddress
import os
import secrets

# Prefer a dedicated salt, fall back to the session secret for a stable value,
# and only mint a throwaway one when nothing is configured.
_SALT = (
    os.environ.get("TRACKING_SALT")
    or os.environ.get("SESSION_SECRET")
    or secrets.token_urlsafe(16)
)


def _network_prefix(ip: str) -> str | None:
    try:
        address = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    bits = 24 if address.version == 4 else 48
    return str(ipaddress.ip_network(f"{address}/{bits}", strict=False))


def coarse_origin(ip: str | None) -> str:
    """Return a salted hash of the network prefix of ``ip`` or ``unknown``."""
    if not ip:
        return "unknown"
    prefix = _network_prefix(ip)
    if prefix is None:
        return "unknown"
    digest = hashlib.sha256(f"{_SALT}:{prefix}".encode("utf-8")).hexdigest()
    # A short prefix of the digest is enough to tell origins apart while
    # keeping the stored value compact.
    return digest[:16]
