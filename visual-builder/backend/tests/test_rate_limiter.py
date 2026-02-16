"""Tests for rate limiter configuration."""
from app.core.rate_limiter import limiter


def test_limiter_exists():
    assert limiter is not None

def test_limiter_default_limits():
    assert limiter._default_limits is not None
