"""Loading tracks on the device: the current one, the next, a seek, a stop,
and what to do when the device cannot play a track."""

from __future__ import annotations

import logging

from casthome.playback.state import PlaybackError, Status
from casthome.subsonic.client import NotAuthenticatedError

from casthome.playback.radio_feed import RadioFeed

log = logging.getLogger(__name__)

MAX_CONSECUTIVE_ERRORS = 5


class Loading(RadioFeed):
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
        if self.target is None and self._taken_over and self.device_uuid is not None:
            await self._connect(self.device_uuid)  # take the device back from the other app
        if self.target is None:
            self._set_position(start_at)
            self.status = Status.STOPPED
            self.notifier.player_changed()
            raise PlaybackError("no_device")
        song = entry.item
        try:
            media = await self._build_media(song, force_fallback)
        except NotAuthenticatedError as exc:
            raise PlaybackError("not_signed_in") from exc
        self._expected_content_id = media.url
        self._clear_preload()  # a LOAD replaces the receiver's whole queue
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
        self._maybe_refill_radio()
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
        self._clear_preload()
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
