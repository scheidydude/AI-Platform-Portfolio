from __future__ import annotations
import time
from collections import defaultdict, deque


class RateLimiter:
    """In-memory sliding-window rate limiter. Safe for single-process async use."""

    def __init__(self, window_seconds: int = 60) -> None:
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, team: str, rpm_limit: int) -> bool:
        """Return True (allowed) or False (rate limited). Records the request if allowed."""
        if rpm_limit <= 0:
            return True
        now = time.monotonic()
        bucket = self._buckets[team]
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= rpm_limit:
            return False
        bucket.append(now)
        return True

    def current_count(self, team: str) -> int:
        now = time.monotonic()
        bucket = self._buckets[team]
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        return len(bucket)
