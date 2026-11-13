"""Cast-facing types shared by the real adapter and the test fake."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_MEDIA_RECEIVER_APP_ID = "CC1AD845"


@dataclass(frozen=True)
class DeviceInfo:
    uuid: str
    name: str
    model: str
    cast_type: str  # "cast" | "audio" | "group"
    host: str
    port: int


@dataclass(frozen=True)
class MediaEvent:
    player_state: str  # PLAYING | PAUSED | BUFFERING | IDLE | UNKNOWN
    idle_reason: str | None  # FINISHED | CANCELLED | INTERRUPTED | ERROR
    content_id: str | None
    current_time: float
    duration: float | None


@dataclass(frozen=True)
class LoadFailedEvent:
    error_code: int


@dataclass(frozen=True)
class ReceiverEvent:
    app_id: str | None
    volume_level: float
    volume_muted: bool


@dataclass(frozen=True)
class ConnectionEvent:
    connected: bool


CastEvent = MediaEvent | LoadFailedEvent | ReceiverEvent | ConnectionEvent
EventSink = Callable[[CastEvent], None]


class CastTarget(Protocol):
    """What the playback coordinator needs from a Cast device."""

    info: DeviceInfo

    async def load(self, url: str, content_type: str, metadata: dict[str, Any], start_at: float) -> None: ...
    async def enqueue(self, url: str, content_type: str, metadata: dict[str, Any]) -> None: ...
    async def play(self) -> None: ...
    async def pause(self) -> None: ...
    async def stop(self) -> None: ...
    async def seek(self, position: float) -> None: ...
    async def set_volume(self, level: float) -> None: ...
    async def set_muted(self, muted: bool) -> None: ...
    async def request_status(self) -> None: ...
    async def disconnect(self) -> None: ...
