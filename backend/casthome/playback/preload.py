"""Preloading (opt-in): the next track is queued on the receiver shortly
before the current one ends, so it starts without a gap."""

from __future__ import annotations

import asyncio
import logging

from casthome.cast.types import (
    MediaEvent,
)
from casthome.playback.state import PlaybackError, Preload

from casthome.playback.loading import Loading

log = logging.getLogger(__name__)

# Preloading (opt-in): the next track is queued on the receiver this long
# before the current one ends. Preloading late keeps the window in which the
# preloaded track can become stale (queue edited) small; a stale preload is
# replaced as soon as the receiver switches to it.
PRELOAD_LEAD_S = 20.0
PRELOAD_SWITCH_TIMEOUT_S = 6.0


class Preloading(Loading):
    async def _maybe_preload(self, ev: MediaEvent) -> None:
        if not self.preload_enabled or self._preload_attempted or self.target is None:
            return
        if not getattr(self.target, "supports_preload", True):
            return
        duration = ev.duration or self.duration
        if not duration or duration - ev.current_time > PRELOAD_LEAD_S:
            return
        self._preload_attempted = True
        index = self.queue.next_index(natural=True)
        if index is None:
            return
        entry = self.queue.entries[index]
        try:
            media = await self._build_media(entry.item, False)
            await self.target.enqueue(media.url, media.content_type, media.metadata)
        except Exception as exc:  # noqa: BLE001 - preloading is best effort
            log.info("Could not preload the next track: %s", exc)
            return
        self._preload = Preload(url=media.url, uid=entry.uid, transcoded=media.transcoded)
        log.info("Preloaded %r", entry.item.title)

    async def _switch_to_preloaded(self) -> None:
        """The receiver started the preloaded track: follow it, or correct it if stale."""
        preload = self._preload
        assert preload is not None
        self._preload = None
        self._preload_attempted = False
        if self._preload_wait is not None:
            self._preload_wait.cancel()
            self._preload_wait = None
        expected_next = self.queue.next_index(natural=True)
        try:
            position = self._position_of(preload.uid)
        except PlaybackError:
            position = None
        if position is None or position != expected_next:
            log.info("Preloaded track is no longer next; loading the right one")
            await self._advance(natural=True)
            return
        self.queue.jump(position)
        song = self.queue.entries[position].item
        self._expected_content_id = preload.url
        self._seen_active = True
        self._fallback_used = False
        self._transcoded = preload.transcoded
        self.duration = song.duration or None
        if self._scrobbler is not None:
            self._scrobbler.track_loaded(song.id, song.duration)
        self.notifier.player_changed()
        self._schedule_save()
        self._maybe_refill_radio()

    def _start_preload_watchdog(self) -> None:
        async def watchdog() -> None:
            await asyncio.sleep(PRELOAD_SWITCH_TIMEOUT_S)
            async with self._lock:
                if self._preload is None:
                    return
                log.info("Receiver did not start the preloaded track; loading it")
                self._clear_preload()
                self._expected_content_id = None
                await self._advance(natural=True)

        if self._preload_wait is None:
            self._preload_wait = asyncio.create_task(watchdog())
