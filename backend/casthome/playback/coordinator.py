"""Server-side playback state machine.

The server is the source of truth: the Cast device only plays the current
track. When it reports IDLE/FINISHED for the media we loaded, the next track
is loaded from here, so playback continues with every browser closed.

How an IDLE status is interpreted (only for the media we loaded last):
- FINISHED     natural end -> advance (repeat-one replays)
- ERROR        unplayable -> retry once transcoded, else skip and notify
- CANCELLED    stopped from elsewhere (remote, Google Home app) -> stopped
- INTERRUPTED  another media replaced ours -> stopped
Statuses for an older media (our previous load) are ignored.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qs, urlparse

from casthome.cast.types import (
    DEFAULT_MEDIA_RECEIVER_APP_ID,
    CastEvent,
    CastTarget,
    ConnectionEvent,
    EventSink,
    LoadFailedEvent,
    MediaEvent,
    ReceiverEvent,
)
from casthome.playback.media import MediaBuilder
from casthome.playback.persistence import QueueStore
from casthome.queue.logic import AddMode, QueueModel, RepeatMode
from casthome.scrobble.scrobbler import Scrobbler
from casthome.subsonic.client import NavidromeUnavailableError, NotAuthenticatedError, SubsonicError
from casthome.subsonic.models import Song

log = logging.getLogger(__name__)

PREVIOUS_RESTART_THRESHOLD_S = 3.0
MAX_CONSECUTIVE_ERRORS = 5
STATUS_POLL_INTERVAL_S = 2.0
POSITION_SAVE_INTERVAL_S = 15.0
SAVE_DEBOUNCE_S = 1.0


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


class PlaybackCoordinator:
    def __init__(
        self,
        connector: Connector,
        media: MediaBuilder,
        store: QueueStore,
        notifier: Notifier | None = None,
        clock: Callable[[], float] = time.time,
        scrobbler: Scrobbler | None = None,
    ) -> None:
        self._connector = connector
        self._scrobbler = scrobbler
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

    # --- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._event_worker(), name="cast-events"),
            asyncio.create_task(self._ticker(), name="playback-ticker"),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await self.flush()
        if self.target is not None:
            try:
                await self.target.disconnect()
            except Exception:  # noqa: BLE001 - best effort at shutdown
                log.exception("Error while disconnecting Cast device")

    async def restore(self) -> None:
        """Load the queue from Navidrome after a (re)start. Never auto-plays."""
        try:
            loaded = await self._store.load()
        except NotAuthenticatedError:
            return
        except (NavidromeUnavailableError, SubsonicError) as exc:
            log.warning("Could not restore the play queue: %s", exc)
            self.notifier.notify("warning", "navidrome_unavailable", {})
            return
        async with self._lock:
            self._apply_loaded(loaded.model, loaded.position, loaded.changed)
            self.device_uuid = loaded.device_uuid
            current = self.queue.current
            # If the selected device still plays our current song, re-attach to it seamlessly.
            self._reattach_song_id = current.item.id if current else None
        self.notifier.queue_changed()
        self.notifier.player_changed()

    async def refresh_from_navidrome(self) -> None:
        """Pick up a play queue saved by another Subsonic client, when idle."""
        if self.status != Status.STOPPED:
            return
        try:
            loaded = await self._store.fetch_if_changed_elsewhere(self._remote_changed)
        except (NotAuthenticatedError, NavidromeUnavailableError, SubsonicError):
            return
        if loaded is None:
            return
        async with self._lock:
            if self.status != Status.STOPPED:
                return
            self._apply_loaded(loaded.model, loaded.position, loaded.changed)
        self.notifier.queue_changed()
        self.notifier.player_changed()

    def _apply_loaded(self, model: QueueModel[Song], position: float, changed: str | None) -> None:
        self.queue = model
        self.queue_version += 1
        self._set_position(position)
        self.duration = model.current.item.duration if model.current else None
        self._remote_changed = changed

    # --- devices -------------------------------------------------------------

    def on_devices_changed(self, available: set[str]) -> None:
        """Connect to the selected device as soon as it is discovered."""
        if self.device_uuid in available and self.target is None and not self._connecting:
            asyncio.create_task(self._connect_selected())

    async def _connect_selected(self) -> None:
        async with self._lock:
            if self.target is not None or self.device_uuid is None:
                return
            try:
                await self._connect(self.device_uuid)
            except PlaybackError as exc:
                self.notifier.notify("error", exc.code, exc.params)

    async def _connect(self, uuid: str) -> None:
        self._connecting = True
        try:
            self.target = await self._connector(uuid, self._events.put_nowait)
            self.connected = True
        except Exception as exc:  # noqa: BLE001 - any connection failure is reported the same way
            log.warning("Cannot connect to Cast device %s: %s", uuid, exc)
            self.target = None
            self.connected = False
            raise PlaybackError("device_unreachable") from exc
        finally:
            self._connecting = False
        self.notifier.player_changed()

    async def select_device(self, uuid: str) -> None:
        async with self._lock:
            if uuid == self.device_uuid and self.target is not None:
                return
            was_active = self.status in (Status.PLAYING, Status.BUFFERING, Status.LOADING)
            position = self.current_position()
            old = self.target
            self._expected_content_id = None
            self._reattach_song_id = None
            self.target = None
            self.connected = False
            self.device_uuid = uuid
            if old is not None:
                try:
                    if was_active or self.status == Status.PAUSED:
                        await old.stop()
                    await old.disconnect()
                except Exception:  # noqa: BLE001 - the old device may already be gone
                    log.info("Previous device did not stop cleanly", exc_info=True)
            self.status = Status.STOPPED
            self._set_position(position)
            self.notifier.player_changed()
            await self._connect(uuid)
            if was_active:
                await self._load_current(position)
            self._schedule_save()

    # --- commands ------------------------------------------------------------

    async def play_songs(self, songs: list[Song], start_index: int = 0) -> None:
        async with self._lock:
            self.queue.replace(songs, start_index)
            self._queue_mutated()
            await self._load_current(0)

    async def add_songs(self, songs: list[Song], mode: AddMode) -> None:
        async with self._lock:
            current_changed = self.queue.add(songs, mode)
            self._queue_mutated()
            if mode == AddMode.NOW or (current_changed and self.status != Status.STOPPED):
                await self._load_current(0)
            elif current_changed:
                self._set_position(0)
                self.notifier.player_changed()

    async def play(self) -> None:
        async with self._lock:
            if self.status == Status.PAUSED and self.target is not None and self._expected_content_id:
                await self._device_call(self.target.play())
            elif self.status == Status.STOPPED and self.queue.current is not None:
                await self._load_current(self.position)

    async def pause(self) -> None:
        async with self._lock:
            if self.target is not None and self.status in (Status.PLAYING, Status.BUFFERING):
                await self._device_call(self.target.pause())

    async def toggle(self) -> None:
        if self.status in (Status.PLAYING, Status.BUFFERING, Status.LOADING):
            await self.pause()
        else:
            await self.play()

    async def stop_playback(self) -> None:
        async with self._lock:
            await self._stop_device()
            self._schedule_save()

    async def next(self) -> None:
        async with self._lock:
            await self._advance(natural=False)

    async def previous(self) -> None:
        async with self._lock:
            if self.current_position() > PREVIOUS_RESTART_THRESHOLD_S:
                await self._seek(0)
                return
            index = self.queue.previous_index()
            if index is None:
                await self._seek(0)
                return
            self.queue.jump(index)
            await self._start_or_cue()

    async def jump(self, index: int) -> None:
        async with self._lock:
            try:
                self.queue.jump(index)
            except IndexError as exc:
                raise PlaybackError("invalid_queue_index") from exc
            await self._load_current(0)

    def _position_of(self, uid: int) -> int:
        for position, entry in enumerate(self.queue.entries):
            if entry.uid == uid:
                return position
        raise PlaybackError("invalid_queue_index")

    async def jump_uid(self, uid: int) -> None:
        async with self._lock:
            self.queue.jump(self._position_of(uid))
            await self._load_current(0)

    async def remove_entry(self, uid: int) -> None:
        async with self._lock:
            current_removed = self.queue.remove(self._position_of(uid))
            self._queue_mutated()
            if not current_removed:
                return
            if self.status == Status.STOPPED or self.queue.current is None:
                await self._stop_device()
                self._set_position(0)
                self.duration = self.queue.current.item.duration if self.queue.current else None
                self.notifier.player_changed()
            else:
                await self._load_current(0)

    async def move_entry(self, uid: int, to_index: int) -> None:
        async with self._lock:
            if not 0 <= to_index < len(self.queue):
                raise PlaybackError("invalid_queue_index")
            self.queue.move(self._position_of(uid), to_index)
            self._queue_mutated()

    async def seek(self, position: float) -> None:
        async with self._lock:
            await self._seek(position)

    async def set_mode(self, shuffle: bool | None = None, repeat: RepeatMode | None = None) -> None:
        async with self._lock:
            if repeat is not None:
                self.queue.repeat = repeat
            if shuffle is not None and shuffle != self.queue.shuffle:
                self.queue.set_shuffle(shuffle)
                self._queue_mutated()
            else:
                self._schedule_save()
            self.notifier.player_changed()

    async def clear(self) -> None:
        async with self._lock:
            await self._stop_device()
            self.queue.clear()
            self._set_position(0)
            self.duration = None
            self._queue_mutated()

    async def set_volume(self, level: float) -> None:
        async with self._lock:
            if self.target is None:
                raise PlaybackError("no_device")
            await self._device_call(self.target.set_volume(level))

    async def set_muted(self, muted: bool) -> None:
        async with self._lock:
            if self.target is None:
                raise PlaybackError("no_device")
            await self._device_call(self.target.set_muted(muted))

    # --- internals: loading --------------------------------------------------

    async def _start_or_cue(self) -> None:
        """Play the new current entry if we were playing, otherwise just cue it."""
        if self.status == Status.STOPPED:
            self._set_position(0)
            self.duration = self.queue.current.item.duration if self.queue.current else None
            self.notifier.player_changed()
            self._schedule_save()
        else:
            await self._load_current(0)

    async def _load_current(self, start_at: float, force_fallback: bool = False) -> None:
        entry = self.queue.current
        if entry is None:
            await self._stop_device()
            return
        if self.target is None:
            self._set_position(start_at)
            self.status = Status.STOPPED
            self.notifier.player_changed()
            raise PlaybackError("no_device")
        song = entry.item
        try:
            media = await self._media.build(song, force_fallback=force_fallback)
        except NotAuthenticatedError as exc:
            raise PlaybackError("not_signed_in") from exc
        self._expected_content_id = media.url
        self._seen_active = False
        self._fallback_used = force_fallback
        if self._scrobbler is not None:
            self._scrobbler.track_loaded(song.id, song.duration)
        self._transcoded = media.transcoded
        self._reattach_song_id = None
        self.status = Status.LOADING
        self.duration = song.duration or None
        self._set_position(start_at)
        self.notifier.player_changed()
        self._schedule_save()
        log.info("Loading %r on %s%s", song.title, self.device_uuid, " (transcoded)" if media.transcoded else "")
        await self._device_call(self.target.load(media.url, media.content_type, media.metadata, start_at))

    async def _advance(self, natural: bool) -> None:
        index = self.queue.next_index(natural=natural)
        if index is None:
            await self._stop_device()
            self._set_position(0)
            self.notifier.player_changed()
            self._schedule_save()
            if natural:
                self.notifier.notify("info", "queue_ended", {})
            return
        self.queue.jump(index)
        if natural:
            await self._load_current(0)
        else:
            await self._start_or_cue()

    async def _seek(self, position: float) -> None:
        position = max(0.0, position)
        if self.duration:
            position = min(position, self.duration)
        if self.target is not None and self._expected_content_id and self.status != Status.STOPPED:
            if self._transcoded:
                # A transcoded stream cannot be seeked reliably: reload at the offset.
                await self._load_current(position, force_fallback=self._fallback_used)
            else:
                await self._device_call(self.target.seek(position))
                self._set_position(position)
        else:
            self._set_position(position)
        self.notifier.player_changed()
        self._schedule_save()

    async def _stop_device(self) -> None:
        position = self.current_position()
        expected, self._expected_content_id = self._expected_content_id, None
        if self.target is not None and expected is not None:
            try:
                await self.target.stop()
            except Exception:  # noqa: BLE001 - stopping an unreachable device is not an error
                log.info("Stop command failed", exc_info=True)
        self.status = Status.STOPPED
        self._set_position(position)
        self.notifier.player_changed()

    async def _device_call(self, call: Awaitable[None]) -> None:
        try:
            await call
        except Exception as exc:  # noqa: BLE001 - pychromecast raises many unrelated types
            log.warning("Cast command failed: %s", exc)
            raise PlaybackError("device_unreachable") from exc

    # --- internals: device events --------------------------------------------

    async def _event_worker(self) -> None:
        while True:
            event = await self._events.get()
            try:
                async with self._lock:
                    await self._handle_event(event)
            except PlaybackError as exc:
                self.notifier.notify("error", exc.code, exc.params)
            except Exception:  # noqa: BLE001 - keep the worker alive
                log.exception("Error while handling Cast event %r", event)

    async def _handle_event(self, event: CastEvent) -> None:
        if isinstance(event, MediaEvent):
            await self._on_media(event)
        elif isinstance(event, LoadFailedEvent):
            if self._expected_content_id is not None:
                await self._on_error()
        elif isinstance(event, ReceiverEvent):
            await self._on_receiver(event)
        elif isinstance(event, ConnectionEvent):
            if event.connected != self.connected:
                self.connected = event.connected
                if not event.connected:
                    self.notifier.notify("warning", "device_disconnected", {})
                elif self.target is not None:
                    await self.target.request_status()
                self.notifier.player_changed()

    def _matches_reattach(self, content_id: str | None) -> bool:
        if not self._reattach_song_id or not content_id:
            return False
        query = parse_qs(urlparse(content_id).query)
        return query.get("id") == [self._reattach_song_id] and query.get("c") == ["CastHome"]

    async def _on_media(self, ev: MediaEvent) -> None:
        if self._expected_content_id is None:
            if ev.player_state in ("PLAYING", "PAUSED", "BUFFERING") and self._matches_reattach(ev.content_id):
                log.info("Re-attached to media already playing on the device")
                self._expected_content_id = ev.content_id
                self._seen_active = True
                self._reattach_song_id = None
                self._transcoded = "format=" in (ev.content_id or "")
                if self._scrobbler is not None and self.queue.current is not None:
                    self._scrobbler.track_loaded(self.queue.current.item.id, self.queue.current.item.duration)
            else:
                return
        if ev.content_id and ev.content_id != self._expected_content_id:
            return  # status for a media we replaced

        if ev.player_state in ("PLAYING", "PAUSED", "BUFFERING"):
            self._seen_active = True
            self.status = {"PLAYING": Status.PLAYING, "PAUSED": Status.PAUSED}.get(ev.player_state, Status.BUFFERING)
            if ev.player_state == "PLAYING":
                self._consecutive_errors = 0
            if ev.duration:
                self.duration = ev.duration
            self._set_position(ev.current_time)
            self.notifier.player_changed()
            await self._report_progress(ev)
            return

        if ev.player_state != "IDLE":
            return
        if ev.idle_reason == "ERROR":
            await self._on_error()
        elif ev.idle_reason == "FINISHED" and self._seen_active:
            self._expected_content_id = None
            await self._advance(natural=True)
        elif ev.idle_reason in ("CANCELLED", "INTERRUPTED") and self._seen_active:
            log.info("Playback stopped from outside CastHome (%s)", ev.idle_reason)
            self._expected_content_id = None
            self.status = Status.STOPPED
            self.notifier.player_changed()
            self._schedule_save()

    async def _report_progress(self, ev: MediaEvent) -> None:
        if self._scrobbler is None or self.queue.current is None:
            return
        if ev.player_state == "PLAYING":
            await self._scrobbler.progress(self.queue.current.item.id, ev.current_time)
        else:
            self._scrobbler.stopped()

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

    async def _on_error(self) -> None:
        entry = self.queue.current
        self._expected_content_id = None
        if entry is None:
            return
        if not self._fallback_used:
            log.info("Cast could not play %r; retrying transcoded", entry.item.title)
            await self._load_current(0, force_fallback=True)
            return
        self._consecutive_errors += 1
        self.notifier.notify("error", "track_unplayable", {"title": entry.item.title})
        if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            await self._stop_device()
            self.notifier.notify("error", "too_many_errors", {})
            return
        # Status is still LOADING/PLAYING here, so _advance loads the next track.
        await self._advance(natural=False)

    async def _on_receiver(self, ev: ReceiverEvent) -> None:
        changed = (ev.volume_level, ev.volume_muted) != (self.volume, self.muted)
        self.volume, self.muted = ev.volume_level, ev.volume_muted
        if (
            self._expected_content_id is not None
            and self._seen_active
            and ev.app_id != DEFAULT_MEDIA_RECEIVER_APP_ID
        ):
            log.info("Another app took over the device (%s)", ev.app_id)
            self._expected_content_id = None
            self.status = Status.STOPPED
            self.notifier.notify("warning", "device_taken_over", {})
            self._schedule_save()
            changed = True
        if changed:
            self.notifier.player_changed()

    # --- internals: position & persistence -----------------------------------

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

    async def _ticker(self) -> None:
        while True:
            await asyncio.sleep(STATUS_POLL_INTERVAL_S)
            try:
                if self.target is not None and self.status in (Status.PLAYING, Status.BUFFERING):
                    await self.target.request_status()
                    if self._clock() - self._last_position_save >= POSITION_SAVE_INTERVAL_S:
                        await self.flush()
            except Exception:  # noqa: BLE001 - the ticker must survive device hiccups
                log.debug("Status poll failed", exc_info=True)

    # --- snapshots for the API / WebSocket -----------------------------------

    def player_snapshot(self, device_name: str | None) -> dict[str, Any]:
        current = self.queue.current
        return {
            "device_uuid": self.device_uuid,
            "device_name": device_name,
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
            "items": [{"uid": e.uid, **e.item.model_dump()} for e in self.queue.entries],
        }
