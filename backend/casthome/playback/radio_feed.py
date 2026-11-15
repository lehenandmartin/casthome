"""Endless radio: more tracks are fetched as the queue runs low."""

from __future__ import annotations

import logging

from casthome.background import spawn
from casthome.subsonic.models import Song

from casthome.playback.core import CoordinatorCore

log = logging.getLogger(__name__)

# Fetch more similar tracks when this few are left.
RADIO_REFILL_AT = 5


class RadioFeed(CoordinatorCore):
    def _maybe_refill_radio(self) -> None:
        if (
            self.queue.radio
            and self._radio_builder is not None
            and not self._radio_refilling
            and self.queue.current is not None
            and self.queue.upcoming_context < RADIO_REFILL_AT
        ):
            self._radio_refilling = True
            spawn(self._refill_radio(), name='refill radio')

    async def _refill_radio(self) -> None:
        """Endless radio: add tracks from the artist (artist radio), else tracks
        similar to the last one of the queue."""
        try:
            exclude = {e.item.id for e in self.queue.entries}
            artist = self.queue.radio_artist
            songs: list[Song] = []
            source: str | None = None
            if artist and self._artist_radio_builder is not None:
                songs, source = await self._artist_radio_builder(artist[0], artist[1], exclude)
                if not songs:
                    log.info("Artist radio %r has nothing new: following the last track", artist[1])
            seed = self.queue.entries[-1].item if self.queue.entries else None
            if not songs and seed is not None and self._radio_builder is not None:
                songs, source = await self._radio_builder(seed, exclude)
            async with self._lock:
                if not self.queue.radio or not songs:
                    return
                if artist and self.queue.radio_artist == artist and source not in ("similar_artists", "top_songs"):
                    self.queue.radio_artist = None  # the artist is exhausted: stay a track radio
                self.queue.extend_context(songs)
                self.queue.radio_source = source or self.queue.radio_source
                self._queue_mutated()
                log.info("Radio refilled with %d tracks", len(songs))
        except Exception:  # noqa: BLE001 - a failed refill just means the radio ends later
            log.warning("Radio refill failed", exc_info=True)
        finally:
            self._radio_refilling = False
