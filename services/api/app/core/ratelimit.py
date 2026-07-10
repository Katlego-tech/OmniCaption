"""A tiny in-memory sliding-window rate limiter (per-process, thread-safe).

Sufficient for a single API instance / demo. A multi-instance deployment would
need a shared store (Redis) — noted as a deployment concern, not a code gap.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Allow at most ``max_hits`` events per ``window_s`` for each key."""

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
