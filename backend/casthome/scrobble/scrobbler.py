"""Scrobbling rules, independent of Cast and HTTP.

- "now playing" (submission=false) when a track starts playing;
- a scrobble (submission=true) once the track was really *listened to* for
  half its duration or 4 minutes, whichever comes first. Seeking forward does
  not count as listening.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

SCROBBLE_MAX_S = 240.0
SCROBBLE_FRACTION = 0.5
# Tolerance between how far the position moved and how much wall time passed;
# anything bigger is a seek, not listening.
SEEK_TOLERANCE_S = 2.0

ScrobbleSink = Callable[[str, bool, int | None], Awaitable[None]]


@dataclass
class _Track:
    song_id: str
    duration: float
    started_at_ms: int
    listened: float = 0.0
    last_position: float | None = None
    last_wall: float | None = None
    now_playing_sent: bool = False
    submitted: bool = False


def threshold(duration: float) -> float:
    if duration <= 0:
        return SCROBBLE_MAX_S
    return min(duration * SCROBBLE_FRACTION, SCROBBLE_MAX_S)


class Scrobbler:
    def __init__(self, sink: ScrobbleSink, clock: Callable[[], float] = time.time) -> None:
        self._sink = sink
        self._clock = clock
        self._track: _Track | None = None

    @property
    def listened(self) -> float:
        return self._track.listened if self._track else 0.0

    def track_loaded(self, song_id: str, duration: float) -> None:
        self._track = _Track(song_id, duration, int(self._clock() * 1000))

    def stopped(self) -> None:
        """Pause/stop: the next sample must not count the gap as listening."""
        if self._track is not None:
            self._track.last_position = None
            self._track.last_wall = None

    async def progress(self, song_id: str, position: float) -> None:
        """Called with each PLAYING status of the current track."""
        track = self._track
        if track is None or track.song_id != song_id:
            return
        now = self._clock()
        if not track.now_playing_sent:
            track.now_playing_sent = True
            await self._sink(song_id, False, None)
        if track.last_position is not None and track.last_wall is not None:
            moved = position - track.last_position
            elapsed = now - track.last_wall
            if 0 < moved <= elapsed + SEEK_TOLERANCE_S:
                track.listened += moved
        track.last_position = position
        track.last_wall = now
        if not track.submitted and track.listened >= threshold(track.duration):
            track.submitted = True
            await self._sink(song_id, True, track.started_at_ms)
