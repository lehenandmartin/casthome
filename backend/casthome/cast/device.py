"""pychromecast adapter.

pychromecast runs its own socket thread and calls listeners from it. Every
callback is forwarded to the asyncio loop with call_soon_threadsafe; every
command runs in a worker thread, serialized by a per-device lock.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pychromecast
from pychromecast.controllers.media import STREAM_TYPE_BUFFERED, MediaStatus, MediaStatusListener
from pychromecast.controllers.receiver import CastStatus, CastStatusListener
from pychromecast.socket_client import CONNECTION_STATUS_CONNECTED, ConnectionStatus, ConnectionStatusListener

from casthome.cast.types import (
    CastEvent,
    ConnectionEvent,
    DeviceInfo,
    EventSink,
    LoadFailedEvent,
    MediaEvent,
    ReceiverEvent,
)

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 15.0


class _Listener(MediaStatusListener, CastStatusListener, ConnectionStatusListener):
    def __init__(self, loop: asyncio.AbstractEventLoop, sink: EventSink) -> None:
        self._loop = loop
        self._sink = sink

    def _emit(self, event: CastEvent) -> None:
        self._loop.call_soon_threadsafe(self._sink, event)

    def new_media_status(self, status: MediaStatus) -> None:
        self._emit(
            MediaEvent(
                player_state=status.player_state,
                idle_reason=status.idle_reason,
                content_id=status.content_id,
                current_time=float(status.adjusted_current_time or 0.0),
                duration=status.duration,
            )
        )

    def load_media_failed(self, queue_item_id: int, error_code: int) -> None:
        self._emit(LoadFailedEvent(error_code=error_code))

    def new_cast_status(self, status: CastStatus) -> None:
        self._emit(
            ReceiverEvent(
                app_id=status.app_id,
                volume_level=float(status.volume_level or 0.0),
                volume_muted=bool(status.volume_muted),
            )
        )

    def new_connection_status(self, status: ConnectionStatus) -> None:
        self._emit(ConnectionEvent(connected=status.status == CONNECTION_STATUS_CONNECTED))


class CastDevice:
    def __init__(self, info: DeviceInfo, cast: pychromecast.Chromecast) -> None:
        self.info = info
        self._cast = cast
        self._lock = asyncio.Lock()

    @classmethod
    async def connect(
        cls,
        info: DeviceInfo,
        cast_info: Any,
        zconf: Any,
        sink: EventSink,
    ) -> CastDevice:
        loop = asyncio.get_running_loop()
        # tries=None: pychromecast reconnects forever if the device reboots or drops.
        cast = pychromecast.get_chromecast_from_cast_info(cast_info, zconf, tries=None, retry_wait=5)
        listener = _Listener(loop, sink)
        cast.register_connection_listener(listener)
        cast.register_status_listener(listener)
        cast.media_controller.register_status_listener(listener)
        await asyncio.to_thread(cast.wait, CONNECT_TIMEOUT_S)
        if not cast.socket_client.is_connected:
            await asyncio.to_thread(cast.disconnect, 2)
            raise TimeoutError(f"Could not connect to {info.name}")
        return cls(info, cast)

    async def _run(self, fn: Any, *args: Any, **kwargs: Any) -> None:
        async with self._lock:
            await asyncio.to_thread(fn, *args, **kwargs)

    async def load(self, url: str, content_type: str, metadata: dict[str, Any], start_at: float) -> None:
        await self._run(
            self._cast.media_controller.play_media,
            url,
            content_type,
            stream_type=STREAM_TYPE_BUFFERED,
            metadata=metadata,
            current_time=start_at if start_at > 0 else None,
            autoplay=True,
        )

    async def enqueue(self, url: str, content_type: str, metadata: dict[str, Any]) -> None:
        """QUEUE_INSERT after the current item: the receiver buffers it and plays it gaplessly."""
        await self._run(
            self._cast.media_controller.play_media,
            url,
            content_type,
            stream_type=STREAM_TYPE_BUFFERED,
            metadata=metadata,
            enqueue=True,
        )

    async def play(self) -> None:
        await self._run(self._cast.media_controller.play)

    async def pause(self) -> None:
        await self._run(self._cast.media_controller.pause)

    async def stop(self) -> None:
        await self._run(self._cast.media_controller.stop)

    async def seek(self, position: float) -> None:
        await self._run(self._cast.media_controller.seek, position)

    async def set_volume(self, level: float) -> None:
        await self._run(self._cast.set_volume, max(0.0, min(1.0, level)))

    async def set_muted(self, muted: bool) -> None:
        await self._run(self._cast.set_volume_muted, muted)

    async def request_status(self) -> None:
        if self._cast.media_controller.is_active:
            await self._run(self._cast.media_controller.update_status)

    async def disconnect(self) -> None:
        await asyncio.to_thread(self._cast.disconnect, 5)
