"""Playback state shared by every layer of the coordinator, and what does not
depend on the queue's logic: the position (and when browsers must be told
about it), saving the queue, talking to the device, snapshots for the API.

The coordinator is built in layers, each one in its own module and using the
ones before it:
    core -> radio_feed -> loading -> preload -> events -> coordinator
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

from casthome.cast.types import (
    CastEvent,
    CastTarget,
)
from casthome.playback.media import CastMedia, MediaBuilder
from casthome.playback.persistence import QueueStore
from casthome.playback.radio import ArtistRadioBuilder, RadioBuilder
from casthome.playback.state import Connector, Notifier, PlaybackError, Preload, Status
from casthome.queue.logic import QueueModel
from casthome.scrobble.scrobbler import Scrobbler
from casthome.subsonic.client import NavidromeUnavailableError, NotAuthenticatedError, SubsonicError
from casthome.subsonic.models import Song

log = logging.getLogger(__name__)

# A polled position this far from where browsers place it is sent to them.
POSITION_DRIFT_S = 1.0
SAVE_DEBOUNCE_S = 1.0


class CoordinatorCore:
    def __init__(
        self,
        connector: Connector,
        media: MediaBuilder,
        store: QueueStore,
        notifier: Notifier | None = None,
        clock: Callable[[], float] = time.time,
        scrobbler: Scrobbler | None = None,
        preload_next: bool = False,
        radio_builder: RadioBuilder | None = None,
        artist_radio_builder: ArtistRadioBuilder | None = None,
    ) -> None:
        self._radio_builder = radio_builder
        self._artist_radio_builder = artist_radio_builder
        self._connection_id = 0
        self._radio_refilling = False
        self._connector = connector
        self._scrobbler = scrobbler
        self.preload_enabled = preload_next
        self._preload: Preload | None = None
        # (status, position, clock) of the last player state sent to browsers.
        self._sent: tuple[Status, float, float] | None = None
        self._preload_attempted = False
        self._preload_wait: asyncio.Task[None] | None = None
        self._media = media
        self._store = store
        self.notifier = notifier or Notifier()
        self._clock = clock

        self.queue: QueueModel[Song] = QueueModel()
        self.queue_version = 0
        self.device_uuid: str | None = None
        self.target: CastTarget | None = None
        self.connected = False
        self.status = Status.STOPPED
        self.position = 0.0
        self.position_ts = clock()
        self.duration: float | None = None
        self.volume = 0.0
        self.muted = False

        self._lock = asyncio.Lock()
        self._events: asyncio.Queue[CastEvent] = asyncio.Queue()
        self._expected_content_id: str | None = None
        self._seen_active = False  # our media reached PLAYING/PAUSED/BUFFERING
        self._fallback_used = False
        self._transcoded = False
        self._consecutive_errors = 0
        self._reattach_song_id: str | None = None
        self._connecting = False
        self._remote_changed: str | None = None
        self._last_position_save = 0.0
        self._save_task: asyncio.Task[None] | None = None
        self._tasks: list[asyncio.Task[None]] = []

    def _position_of(self, uid: int) -> int:
        for position, entry in enumerate(self.queue.entries):
            if entry.uid == uid:
                return position
        raise PlaybackError("invalid_queue_index")

    def _is_browser(self) -> bool:
        return self.target is not None and self.target.info.cast_type == "browser"

    async def _build_media(self, song: Song, force_fallback: bool) -> CastMedia:
        if self._is_browser():
            return self._media.build_for_browser(song, force_fallback)
        return await self._media.build(song, force_fallback=force_fallback)

    async def _device_call(self, call: Awaitable[None]) -> None:
        try:
            await call
        except Exception as exc:  # noqa: BLE001 - pychromecast raises many unrelated types
            log.warning("Cast command failed: %s", exc)
            raise PlaybackError("device_unreachable") from exc

    def _clear_preload(self) -> None:
        self._preload = None
        self._preload_attempted = False
        if self._preload_wait is not None:
            self._preload_wait.cancel()
            self._preload_wait = None

    def update_song_flags(self, song_id: str, **changes: Any) -> None:
        """Reflect a star/rating change in the queue copies of a song."""
        changed = False
        for i, entry in enumerate(self.queue.entries):
            if entry.item.id == song_id:
                self.queue.entries[i] = replace(entry, item=entry.item.model_copy(update=changes))
                changed = True
        if changed:
            self.queue_version += 1
            self.notifier.queue_changed()
            self.notifier.player_changed()

    # --- internals: position & persistence -----------------------------------

    def _position_drifted(self) -> bool:
        """Is the position far from where browsers place it, moving on from the
        last state they were sent?"""
        if self._sent is None:
            return True
        status, position, at = self._sent
        if status != self.status:
            return True
        expected = position + (self._clock() - at) if status == Status.PLAYING else position
        return abs(self.position - expected) > POSITION_DRIFT_S

    def _set_position(self, position: float) -> None:
        self.position = max(0.0, position)
        self.position_ts = self._clock()

    def current_position(self) -> float:
        if self.status == Status.PLAYING:
            pos = self.position + (self._clock() - self.position_ts)
            return min(pos, self.duration) if self.duration else pos
        return self.position

    def _queue_mutated(self) -> None:
        self.queue_version += 1
        self.notifier.queue_changed()
        self.notifier.player_changed()
        self._schedule_save()

    def _schedule_save(self) -> None:
        if self._save_task is not None and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = asyncio.create_task(self._save_later())

    async def _save_later(self) -> None:
        await asyncio.sleep(SAVE_DEBOUNCE_S)
        await self.flush()

    async def flush(self) -> None:
        self._last_position_save = self._clock()
        try:
            await self._store.save(self.queue, self.current_position(), self.device_uuid)
        except NotAuthenticatedError:
            pass
        except (NavidromeUnavailableError, SubsonicError) as exc:
            log.warning("Could not save the play queue to Navidrome: %s", exc)

    # --- snapshots for the API / WebSocket -----------------------------------

    def player_snapshot(self, device_name: str | None) -> dict[str, Any]:
        current = self.queue.current
        # What browsers now base the position on (see _position_drifted).
        self._sent = (self.status, self.current_position(), self._clock())
        return {
            "device_uuid": self.device_uuid,
            "device_name": device_name,
            "device_type": self.target.info.cast_type if self.target is not None else None,
            "connected": self.connected and self.target is not None,
            "status": self.status.value,
            "index": self.queue.index,
            "current": current.item.model_dump() if current else None,
            # Position at snapshot time; clients interpolate from when they receive it,
            # so client/server clock skew does not matter.
            "position": self.current_position(),
            "duration": self.duration,
            "volume": self.volume,
            "muted": self.muted,
            "shuffle": self.queue.shuffle,
            "repeat": self.queue.repeat.value,
            "queue_version": self.queue_version,
        }

    def queue_snapshot(self) -> dict[str, Any]:
        return {
            "version": self.queue_version,
            "index": self.queue.index,
            "context_name": self.queue.context_name,
            "radio": self.queue.radio,
            "radio_source": self.queue.radio_source if self.queue.radio else None,
            "items": [{"uid": e.uid, "queued": e.queued, **e.item.model_dump()} for e in self.queue.entries],
        }
