"""Radios, like Spotify's: endless lists of similar tracks.

Track radio: a track followed by similar tracks. Sources, tried in order
until one returns something new:
1. getSimilarSongs(track id): on Navidrome, served by AudioMuse-AI (sonic
   similarity) when that plugin is active, else by Last.fm and other agents.
2. getSimilarSongs2(artist id): the artist and similar artists (Last.fm).
3. getTopSongs(artist): the artist's popular tracks.

Artist radio: the artist and similar artists, shuffled. Sources:
1. getSimilarSongs2(artist id), asked for a large pool (Last.fm data; the
   share of the artist's own tracks follows how many the library has, up to
   two thirds for an artist with many tracks).
2. getTopSongs(artist): the artist's popular tracks.
Each batch keeps the artist to about a third (ARTIST_SHARE), spread through
the batch, and uses at most a quarter of the artist's tracks left
(ARTIST_SPREAD), so a small catalogue lasts several batches. Once only the artist's own tracks are left, a refill returns
nothing, so the radio goes on from the last track (other artists).
(getSimilarSongs with an artist id returns the same mix: AudioMuse-AI only
works from a track.)

A failing or empty source is skipped, so a radio still works when a service
behind Navidrome is down; if all fail, the caller gets an empty list.
"""

from __future__ import annotations

import logging
import math
import random
from collections.abc import Awaitable, Callable
from typing import Protocol

from casthome.subsonic.client import NavidromeUnavailableError, SubsonicError
from casthome.subsonic.models import Song

log = logging.getLogger(__name__)

RADIO_BATCH = 50
# Artist radio: tracks asked for at once, shuffled, then RADIO_BATCH queued.
ARTIST_POOL = 200
# Artist radio: at most this share of a batch is the artist's own tracks...
ARTIST_SHARE = 1 / 3
# ...and at most 1/ARTIST_SPREAD of those left, so an artist with few tracks
# keeps coming back over several batches instead of all at once.
ARTIST_SPREAD = 4


class SimilarSource(Protocol):
    async def extensions(self) -> set[str]: ...
    async def get_similar_songs(self, item_id: str, count: int = 50) -> list[Song]: ...
    async def get_similar_songs2(self, artist_id: str, count: int = 50) -> list[Song]: ...
    async def get_top_songs(self, artist: str, count: int = 50) -> list[Song]: ...


# (songs, source label) - labels: audiomuse | similar | similar_artists | top_songs
RadioBuilder = Callable[[Song, set[str]], Awaitable[tuple[list[Song], str | None]]]
# (artist id, artist name, ids to skip) -> (songs, source label)
ArtistRadioBuilder = Callable[[str, str, set[str]], Awaitable[tuple[list[Song], str | None]]]
Attempt = tuple[str, Callable[[], Awaitable[list[Song]]]]


async def first_fresh(attempts: list[Attempt], exclude: set[str], what: str) -> tuple[list[Song], str | None]:
    """The first source that returns tracks not in `exclude`, and its label."""
    last_error: Exception | None = None
    for source, fetch in attempts:
        try:
            songs = await fetch()
        except (SubsonicError, NavidromeUnavailableError) as exc:
            log.warning("Radio source %s failed: %s", source, exc)
            last_error = exc
            continue
        fresh = dedupe(songs, exclude)
        if fresh:
            log.info("Radio for %r: %d tracks from %s", what, len(fresh), source)
            return fresh, source
        log.info("Radio source %s returned nothing new for %r", source, what)
    if isinstance(last_error, NavidromeUnavailableError):
        raise last_error
    return [], None


def make_radio_builder(client: SimilarSource, count: int = RADIO_BATCH) -> RadioBuilder:
    async def build(seed: Song, exclude: set[str]) -> tuple[list[Song], str | None]:
        try:
            sonic = "sonicSimilarity" in await client.extensions()
        except (SubsonicError, NavidromeUnavailableError):
            sonic = False
        attempts: list[Attempt] = [
            ("audiomuse" if sonic else "similar", lambda: client.get_similar_songs(seed.id, count)),
        ]
        if seed.artist_id:
            attempts.append(("similar_artists", lambda: client.get_similar_songs2(seed.artist_id or "", count)))
        if seed.artist:
            attempts.append(("top_songs", lambda: client.get_top_songs(seed.artist, count)))
        return await first_fresh(attempts, exclude | {seed.id}, seed.title)

    return build


def make_artist_radio_builder(
    client: SimilarSource,
    count: int = RADIO_BATCH,
    pool: int = ARTIST_POOL,
    rng: random.Random | None = None,
) -> ArtistRadioBuilder:
    shuffle = (rng or random.Random()).shuffle

    async def build(artist_id: str, artist_name: str, exclude: set[str]) -> tuple[list[Song], str | None]:
        attempts: list[Attempt] = [
            ("similar_artists", lambda: client.get_similar_songs2(artist_id, pool)),
            ("top_songs", lambda: client.get_top_songs(artist_name, pool)),
        ]
        songs, source = await first_fresh(attempts, exclude, artist_name)
        # Navidrome returns the same order every time: shuffle, so each batch mixes
        # the artist and similar artists differently.
        shuffle(songs)
        name = artist_name.casefold()
        own = [s for s in songs if s.artist_id == artist_id or name in s.artist.casefold()]
        others = [s for s in songs if not (s.artist_id == artist_id or name in s.artist.casefold())]
        if not others:
            # Only the artist left: fine to start with (no similar artists known),
            # but a refill hands over to the track radio instead.
            return (own[:count], source) if not exclude else ([], None)
        return mix_artist(own, others, count), source

    return build


def mix_artist(own: list[Song], others: list[Song], count: int, share: float = ARTIST_SHARE) -> list[Song]:
    """Up to `count` tracks, at most `share` of them the artist's (at least one),
    spread evenly among the others' tracks."""
    wanted_own = min(len(own), max(1, round(count * share)), max(1, math.ceil(len(own) / ARTIST_SPREAD)))
    n_others = min(len(others), count - wanted_own)
    # Few other tracks left: fewer of the artist's too, to keep the share.
    n_own = min(wanted_own, max(1, math.ceil(n_others * share / (1 - share))))
    picked_own, picked_others = own[:n_own], others[:n_others]
    total = n_own + n_others
    # The artist's tracks at evenly spaced positions, the first one at the start.
    slots = {round(i * total / n_own) for i in range(n_own)} if n_own else set()
    out: list[Song] = []
    it_own, it_others = iter(picked_own), iter(picked_others)
    for position in range(total):
        out.append(next(it_own) if position in slots else next(it_others))
    return out


def dedupe(songs: list[Song], exclude: set[str]) -> list[Song]:
    seen = set(exclude)
    out: list[Song] = []
    for song in songs:
        if song.id not in seen:
            seen.add(song.id)
            out.append(song)
    return out
