"""What the playback modules share: the player status, user-facing errors,
the callbacks that tell browsers about changes, and a preloaded track."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from casthome.cast.types import CastTarget, EventSink


@dataclass
class Preload:
    """The next track, already queued on the receiver (see preload.py)."""

    url: str
    uid: int
    transcoded: bool


class Status(StrEnum):
    STOPPED = "stopped"
    LOADING = "loading"
    BUFFERING = "buffering"
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackError(Exception):
    """A user-facing command failure. `code` is translated by the frontend."""

    def __init__(self, code: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.params = params or {}


Connector = Callable[[str, EventSink], Awaitable[CastTarget]]


@dataclass
class Notifier:
    player_changed: Callable[[], None] = lambda: None
    queue_changed: Callable[[], None] = lambda: None
    notify: Callable[[str, str, dict[str, Any]], None] = lambda level, code, params: None

