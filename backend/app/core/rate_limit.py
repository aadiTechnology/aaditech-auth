"""In-process sliding-window rate limiter.

The limiter is per process. Run a single API worker or replace it with a
shared store before horizontal scaling.
"""

import threading
import time
from collections import defaultdict, deque

from app.common.exceptions import AppError, ErrorCode


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._events.clear()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] > window_seconds:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                raise AppError(
                    ErrorCode.RATE_LIMITED,
                    "Too many attempts. Please wait and try again.",
                    429,
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)


limiter = InMemoryRateLimiter()
