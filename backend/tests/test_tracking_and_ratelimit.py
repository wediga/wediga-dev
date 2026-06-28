"""Unit tests for the data-sparse origin and the rate limiter."""

from app.auth.ratelimit import RateLimiter
from app.recruiter.tracking import coarse_origin


def test_coarse_origin_groups_same_network_and_hides_address() -> None:
    a = coarse_origin("203.0.113.10")
    b = coarse_origin("203.0.113.250")
    c = coarse_origin("198.51.100.10")
    # Same /24 maps to the same token, a different network to a different one.
    assert a == b
    assert a != c
    # The stored value never contains the original address.
    assert "203.0.113" not in a
    assert "." not in a


def test_coarse_origin_handles_ipv6_and_garbage() -> None:
    assert coarse_origin("2001:db8::1") == coarse_origin("2001:db8::ffff")
    assert coarse_origin("not-an-ip") == "unknown"
    assert coarse_origin(None) == "unknown"


def test_rate_limiter_allows_up_to_max_then_blocks() -> None:
    limiter = RateLimiter(max_attempts=2, window_seconds=300)
    assert limiter.hit("ip") is True
    assert limiter.hit("ip") is True
    assert limiter.hit("ip") is False
    # A different key has its own budget.
    assert limiter.hit("other") is True
    # Resetting the key restores the budget.
    limiter.reset("ip")
    assert limiter.hit("ip") is True
