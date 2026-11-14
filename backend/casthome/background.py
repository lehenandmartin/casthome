"""Fire-and-forget tasks that are neither lost nor silent.

asyncio keeps only a weak reference to a task: one started with a bare
`asyncio.create_task(...)` and not stored anywhere can be garbage-collected
before it finishes. `spawn` keeps each task until it is done, and logs an
error it ended with (otherwise only printed, if ever, when it is collected).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

log = logging.getLogger(__name__)

_running: set[asyncio.Task[Any]] = set()


def spawn(coro: Coroutine[Any, Any, Any], name: str | None = None) -> asyncio.Task[Any]:
    """Run `coro` in the background, keeping the task alive until it ends."""
    task = asyncio.create_task(coro, name=name)
    _running.add(task)
    task.add_done_callback(_finished)
    return task


def _finished(task: asyncio.Task[Any]) -> None:
    _running.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        log.error("Background task %s failed", task.get_name(), exc_info=exc)
