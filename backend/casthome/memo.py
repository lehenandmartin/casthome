"""A value remembered for a short while (e.g. a slow Navidrome answer).

`get(load)` returns the remembered value while it is younger than `ttl`
seconds, else calls `load` (once, even for callers arriving meanwhile).
`forget()` drops it, after a change that makes it wrong. A failed load is not
remembered.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class Memo(Generic[T]):
    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl = ttl
        self._clock = clock
        self._value: T | None = None
        self._at: float | None = None
        self._lock = asyncio.Lock()
        self._generation = 0

    def _fresh(self) -> bool:
        return self._at is not None and self._clock() - self._at < self.ttl

    async def get(self, load: Callable[[], Awaitable[T]]) -> T:
        if self._fresh():
            return self._value  # type: ignore[return-value]
        async with self._lock:
            if self._fresh():
                return self._value  # type: ignore[return-value]
            generation = self._generation
            value = await load()
            # Forgotten while loading: the value may predate the change.
            if generation == self._generation:
                self._value, self._at = value, self._clock()
            return value

    def forget(self) -> None:
        self._value, self._at = None, None
        self._generation += 1
