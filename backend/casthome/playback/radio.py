"""Track radio: a track followed by similar tracks, like Spotify's radio.

Sources, tried in order until one returns something new:
1. getSimilarSongs(track id): on Navidrome, served by AudioMuse-AI (sonic
   similarity) when that plugin is active, else by Last.fm and other agents.
2. getSimilarSongs2(artist id): the artist and similar artists (Last.fm).
3. getTopSongs(artist): the artist's popular tracks.
A failing or empty source is skipped, so the radio still works when a
service behind Navidrome is down; if all fail, the caller gets an empty list.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from casthome.subsonic.client import NavidromeUnavailableError, SubsonicError
from casthome.subsonic.models import Song

log = logging.getLogger(__name__)

RADIO_BATCH = 50


class SimilarSource(Protocol):
    async def extensions(self) -> set[str]: ...
    async def get_similar_songs(self, item_id: str, count: int = 50) -> list[Song]: ...
    async def get_similar_songs2(self, artist_id: str, count: int = 50) -> list[Song]: ...
    async def get_top_songs(self, artist: str, count: int = 50) -> list[Song]: ...


# (songs, source label) - labels: audiomuse | similar | similar_artists | top_songs
RadioBuilder = Callable[[Song, set[str]], Awaitable[tuple[list[Song], str | None]]]


def make_radio_builder(client: SimilarSource, count: int = RADIO_BATCH) -> RadioBuilder:
    async def build(seed: Song, exclude: set[str]) -> tuple[list[Song], str | None]:
        try:
            sonic = "sonicSimilarity" in await client.extensions()
        except (SubsonicError, NavidromeUnavailableError):
            sonic = False
        attempts: list[tuple[str, Callable[[], Awaitable[list[Song]]]]] = [
            ("audiomuse" if sonic else "similar", lambda: client.get_similar_songs(seed.id, count)),
        ]
        if seed.artist_id:
            attempts.append(("similar_artists", lambda: client.get_similar_songs2(seed.artist_id or "", count)))
        if seed.artist:
            attempts.append(("top_songs", lambda: client.get_top_songs(seed.artist, count)))

        last_error: Exception | None = None
        for source, fetch in attempts:
            try:
                songs = await fetch()
            except (SubsonicError, NavidromeUnavailableError) as exc:
                log.warning("Radio source %s failed: %s", source, exc)
                last_error = exc
                continue
            fresh = dedupe(songs, exclude | {seed.id})
            if fresh:
                log.info("Radio for %r: %d tracks from %s", seed.title, len(fresh), source)
                return fresh, source
            log.info("Radio source %s returned nothing new for %r", source, seed.title)
        if last_error is not None and isinstance(last_error, NavidromeUnavailableError):
            raise last_error
        return [], None

    return build


def dedupe(songs: list[Song], exclude: set[str]) -> list[Song]:
    seen = set(exclude)
    out: list[Song] = []
    for song in songs:
        if song.id not in seen:
            seen.add(song.id)
            out.append(song)
    return out
