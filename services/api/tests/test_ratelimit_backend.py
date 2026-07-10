"""Rate-limiter backend selection + the shared (Redis) limiter's window logic."""

from __future__ import annotations

from app.core.config import Settings
from app.core.ratelimit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    build_rate_limiter,
)


class FakeRedis:
    """Minimal INCR/EXPIRE store; optionally raises to simulate an outage."""

    def __init__(self, *, broken: bool = False) -> None:
        self.store: dict[str, int] = {}
        self.expires: dict[str, int] = {}
        self._broken = broken

    def incr(self, key: str) -> int:
        if self._broken:
            raise ConnectionError("redis down")
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, seconds: int) -> None:
        if self._broken:
            raise ConnectionError("redis down")
        self.expires[key] = seconds


def test_build_defaults_to_in_memory(tmp_path) -> None:
    limiter = build_rate_limiter(Settings(data_dir=tmp_path, _env_file=None))
    assert isinstance(limiter, InMemoryRateLimiter)


def test_build_falls_back_when_redis_unavailable(tmp_path) -> None:
    # A REDIS_URL is set but the redis package/connection is unavailable in CI,
    # so the factory degrades to in-memory rather than crashing at startup.
    limiter = build_rate_limiter(
        Settings(data_dir=tmp_path, redis_url="redis://localhost:6379/0", _env_file=None)
    )
    assert isinstance(limiter, InMemoryRateLimiter)


def test_redis_limiter_enforces_the_cap() -> None:
    limiter = RedisRateLimiter(max_hits=2, window_s=60, client=FakeRedis())
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False  # 3rd exceeds max=2
    assert limiter.allow("other") is True  # independent key


def test_redis_limiter_fails_open_on_outage() -> None:
    # If Redis is unreachable, allow the request (availability over strictness).
    limiter = RedisRateLimiter(max_hits=1, window_s=60, client=FakeRedis(broken=True))
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
