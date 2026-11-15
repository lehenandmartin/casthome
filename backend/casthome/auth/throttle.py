"""Limit password guesses per client address."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable


class LoginThrottle:
    """At most `max_attempts` failed guesses per address in `window_s` seconds.

    A correct password clears the address. Addresses whose guesses have all
    expired are forgotten, so the table stays small however many addresses
    try (at most `max_addresses` are kept: the oldest go first)."""

    def __init__(
        self,
        max_attempts: int = 10,
        window_s: float = 300,
        max_addresses: int = 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_s = window_s
        self.max_addresses = max_addresses
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}

    def check(self, ip: str) -> float | None:
        """Count an attempt from `ip`. Returns None when it may go on, or the
        seconds to wait when it has used up its attempts."""
        now = self._clock()
        self._prune(now)
        window = self._attempts.get(ip)
        if window is None:
            if len(self._attempts) >= self.max_addresses:
                # Dicts keep insertion order: drop the address seen first.
                self._attempts.pop(next(iter(self._attempts)))
            window = self._attempts[ip] = deque()
        if len(window) >= self.max_attempts:
            return max(0.0, window[0] + self.window_s - now)
        window.append(now)
        return None

    def passed(self, ip: str) -> None:
        self._attempts.pop(ip, None)

    def tracked(self) -> int:
        return len(self._attempts)

    def clear(self) -> None:
        self._attempts.clear()

    def _prune(self, now: float) -> None:
        for ip in list(self._attempts):
            window = self._attempts[ip]
            while window and now - window[0] > self.window_s:
                window.popleft()
            if not window:
                del self._attempts[ip]


def retry_after(seconds: float) -> str:
    """Value of a Retry-After header: whole seconds, at least 1."""
    return str(max(1, math.ceil(seconds)))
