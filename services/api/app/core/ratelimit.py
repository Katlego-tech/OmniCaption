"""Rate limiting with a pluggable backend.

Default is an in-memory sliding window (fine for a single instance). Set
``REDIS_URL`` to share limits across instances — the ``redis`` package is an
optional dependency, lazily imported; if it is missing or the URL is
unreachable at startup the factory degrades to in-memory with a warning.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class RateLimiter(Protocol):
    """Anything that decides whether an event for ``key`` is within the limit."""

    def allow(self, key: str) -> bool: ...


class InMemoryRateLimiter:
    """Per-process sliding window. Not shared across instances."""

    def __init__(self, max_hits: int, window_s: float) -> None:
        self._max = max_hits
        self._window = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record an attempt for ``key``; return False if it exceeds the limit."""
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - self._window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._max:
                return False
            bucket.append(now)
            return True


class RedisRateLimiter:
    """Shared fixed-window counter (atomic INCR + EXPIRE) across instances.

    Fixed-window (not sliding) for atomicity without Lua; a burst spanning a
    window boundary can briefly allow up to 2x. Fails open on Redis errors so a
    cache outage degrades to "no limiting" rather than locking everyone out.
    """

    def __init__(self, max_hits: int, window_s: int, client: Any) -> None:
        self._max = max_hits
        self._window = window_s
        self._redis = client

    def allow(self, key: str) -> bool:
        bucket = int(time.time()) // self._window
        redis_key = f"rl:{key}:{bucket}"
        try:
            count = self._redis.incr(redis_key)
            if count == 1:
                self._redis.expire(redis_key, self._window)
            return count <= self._max
        except Exception as exc:  # noqa: BLE001 - availability over strictness
            logger.warning("Rate-limit backend error (%s); failing open.", exc)
            return True


def build_rate_limiter(settings: Any) -> RateLimiter:
    """Pick a limiter from settings: shared Redis when configured, else in-memory."""
    url = getattr(settings, "redis_url", "").strip()
    if url:
        try:
            import redis  # optional dependency

            client = redis.Redis.from_url(url)
            client.ping()
            logger.info("Rate limiting via shared Redis backend.")
            return RedisRateLimiter(settings.rate_limit_max, settings.rate_limit_window_s, client)
        except Exception as exc:  # noqa: BLE001 - degrade, don't crash startup
            logger.warning(
                "REDIS_URL set but Redis is unavailable (%s); using in-memory limiter.", exc
            )
    return InMemoryRateLimiter(settings.rate_limit_max, settings.rate_limit_window_s)
