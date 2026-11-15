"""Server-side playback state machine.

The server is the source of truth: the Cast device only plays the current
track. When it reports the end of the media we loaded, the next track is
loaded from here, so playback continues with every browser closed.

This module holds the commands (play, next, add to queue, select a device...)
and the lifecycle. The rest is in layers, each in its own module:
    core        state, position, saving, snapshots
    radio_feed  endless radio
    loading     loading tracks, seeking, stopping, unplayable tracks
    preload     queuing the next track on the receiver ahead of time
    events      what the device reports
"""

from __future__ import annotations

import asyncio
import logging

from casthome.background import spawn
from casthome.cast.types import (
    CastEvent,
)
from casthome.playback.state import Notifier, PlaybackError, Status
from casthome.queue.logic import AddMode, QueueModel, RepeatMode
from casthome.subsonic.client import NavidromeUnavailableError, NotAuthenticatedError, SubsonicError
from casthome.subsonic.models import Song

from casthome.playback.events import DeviceEvents

log = logging.getLogger(__name__)

PREVIOUS_RESTART_THRESHOLD_S = 3.0
STATUS_POLL_INTERVAL_S = 2.0
POSITION_SAVE_INTERVAL_S = 15.0
REMOTE_REFRESH_INTERVAL_S = 60.0

__all__ = ["Notifier", "PlaybackCoordinator", "PlaybackError", "Status"]


class PlaybackCoordinator(DeviceEvents):
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
            # A browser tab does not survive a restart; Cast devices are reconnected.
            stored = loaded.device_uuid
            self.device_uuid = None if stored and stored.startswith("browser:") else stored
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
            spawn(self._connect_selected(), name='connect device')

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
            # Each connection gets its own sink: events still arriving from a
            # device we left (its last volume, its session closing) are dropped.
            self._connection_id += 1
            connection_id = self._connection_id

            def sink(event: CastEvent) -> None:
                if connection_id == self._connection_id:
                    self._events.put_nowait(event)

            self.target = await self._connector(uuid, sink)
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
            self._connection_id += 1  # ignore whatever the old device still sends
            self._expected_content_id = None
            self._reattach_song_id = None
            self.target = None
            self.connected = False
            self.device_uuid = uuid
            if old is not None:
                try:
                    # End the session on the old device (it goes back to idle),
                    # then drop the connection.
                    await old.quit()
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

    async def play_songs(self, songs: list[Song], start_index: int = 0, context_name: str | None = None) -> None:
        """Play an album/playlist/list; tracks in "next in queue" are kept."""
        async with self._lock:
            self.queue.play_context(songs, start_index, context_name)
            self._queue_mutated()
            await self._load_current(0)

    @property
    def radio_source(self) -> str | None:
        return self.queue.radio_source if self.queue.radio else None

    async def start_radio(self, seed: Song) -> str:
        """Play `seed`, then similar tracks; the radio refills itself as it plays.
        Returns the source used. Tracks in "next in queue" are kept.
        When `seed` is the track being played, it carries on where it is and
        the similar tracks follow it (no restart)."""
        if self._radio_builder is None:
            raise PlaybackError("no_similar_tracks")
        try:
            songs, source = await self._radio_builder(seed, {seed.id})
        except NavidromeUnavailableError as exc:
            raise PlaybackError("navidrome_unavailable") from exc
        if not songs or source is None:
            raise PlaybackError("no_similar_tracks", {"title": seed.title})
        async with self._lock:
            current = self.queue.current
            continuing = current is not None and current.item.id == seed.id
            if continuing:
                self.queue.follow_current(songs, seed.title)
            else:
                self.queue.play_context([seed, *songs], 0, seed.title)
            self.queue.radio = True
            self.queue.radio_source = source
            self._queue_mutated()
            if not continuing:
                await self._load_current(0)
        return source

    async def start_artist_radio(self, artist_id: str, artist_name: str) -> str:
        """Play the artist and similar artists, shuffled, opening with one of the
        artist's tracks; refilled from the artist as it plays. Returns the source.
        Tracks in "next in queue" are kept."""
        if self._artist_radio_builder is None:
            raise PlaybackError("no_similar_tracks", {"title": artist_name})
        try:
            songs, source = await self._artist_radio_builder(artist_id, artist_name, set())
        except NavidromeUnavailableError as exc:
            raise PlaybackError("navidrome_unavailable") from exc
        if not songs or source is None:
            raise PlaybackError("no_similar_tracks", {"title": artist_name})
        own = next((i for i, s in enumerate(songs) if s.artist_id == artist_id), 0)
        songs.insert(0, songs.pop(own))
        async with self._lock:
            self.queue.play_context(songs, 0, artist_name)
            self.queue.radio = True
            self.queue.radio_source = source
            self.queue.radio_artist = (artist_id, artist_name)
            self._queue_mutated()
            await self._load_current(0)
        return source

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

    async def move_entry(self, uid: int, to_index: int, queued: bool | None = None) -> None:
        async with self._lock:
            if not 0 <= to_index < len(self.queue):
                raise PlaybackError("invalid_queue_index")
            self.queue.move(self._position_of(uid), to_index, queued)
            self._queue_mutated()

    async def clear_queued(self) -> None:
        """Empty "next in queue" only; the album or playlist carries on."""
        async with self._lock:
            self.queue.clear_queued()
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

    async def _ticker(self) -> None:
        last_refresh = self._clock()
        while True:
            await asyncio.sleep(STATUS_POLL_INTERVAL_S)
            if self.status == Status.STOPPED and self._clock() - last_refresh >= REMOTE_REFRESH_INTERVAL_S:
                # Idle: pick up a play queue saved by another Subsonic client.
                last_refresh = self._clock()
                await self.refresh_from_navidrome()
            try:
                if self.target is not None and self.status in (Status.PLAYING, Status.BUFFERING):
                    await self.target.request_status()
                    if self._clock() - self._last_position_save >= POSITION_SAVE_INTERVAL_S:
                        await self.flush()
            except Exception:  # noqa: BLE001 - the ticker must survive device hiccups
                log.debug("Status poll failed", exc_info=True)
