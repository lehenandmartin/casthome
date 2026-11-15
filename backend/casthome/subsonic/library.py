"""The library lists the Subsonic API cannot give, whatever the server.

On Navidrome they come from its own API (`NativeClient`). On any other
Subsonic server, favorites come from `getStarred2`, sorted and paged here,
and what only Navidrome can list (every track, play history) is empty: the
interface hides it (see `capabilities`).
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from typing import Any

from casthome.subsonic.client import SubsonicClient
from casthome.subsonic.models import Album, SearchResult, Song
from casthome.subsonic.native import NativeClient, SongSort

NAVIDROME = "navidrome"

StarredProvider = Callable[[], Awaitable[SearchResult]]


def capabilities(server_type: str | None) -> dict[str, bool]:
    """What the interface can offer with this server (None: not known yet)."""
    navidrome = server_type in (None, NAVIDROME)  # assume Navidrome until told otherwise
    return {"all_tracks": navidrome, "play_history": navidrome}


def _text(value: str) -> str:
    return value.casefold()


def sort_songs(songs: list[Song], sort: SongSort) -> list[Song]:
    if sort == "title":
        return sorted(songs, key=lambda s: _text(s.title))
    if sort == "artist":
        return sorted(songs, key=lambda s: (_text(s.artist), _text(s.album), s.disc or 0, s.track or 0))
    if sort == "album":
        return sorted(songs, key=lambda s: (_text(s.album), s.disc or 0, s.track or 0))
    if sort == "frequent":
        return sorted(songs, key=lambda s: s.play_count, reverse=True)
    if sort == "played":
        return sorted(songs, key=lambda s: s.played or "", reverse=True)
    return sorted(songs, key=lambda s: s.created or "", reverse=True)  # "recent": newest additions first


def sort_albums(albums: list[Album], list_type: str) -> list[Album]:
    if list_type == "alphabeticalByName":
        return sorted(albums, key=lambda a: _text(a.name))
    if list_type == "frequent":
        return sorted(albums, key=lambda a: a.play_count, reverse=True)
    if list_type == "recent":
        return sorted(albums, key=lambda a: a.played or "", reverse=True)
    if list_type == "random":
        return random.sample(albums, len(albums))
    return sorted(albums, key=lambda a: a.created or "", reverse=True)  # "newest"


class Library:
    def __init__(self, subsonic: SubsonicClient, native: NativeClient, starred: StarredProvider) -> None:
        self.subsonic = subsonic
        self.native = native
        self._starred = starred

    async def is_navidrome(self) -> bool:
        return await self.subsonic.detect_server_type() == NAVIDROME

    async def get_albums(self, list_type: str = "newest", offset: int = 0, size: int = 40, starred: bool = False) -> list[Album]:
        if await self.is_navidrome():
            return await self.native.get_albums(list_type, offset, size, starred=starred)
        if not starred:
            return await self.subsonic.get_album_list(list_type, size, offset)
        albums = sort_albums((await self._starred()).albums, list_type)
        return albums[offset : offset + size]

    async def get_songs(
        self,
        sort: SongSort = "recent",
        offset: int = 0,
        size: int = 100,
        starred: bool = False,
        artist_id: str | None = None,
    ) -> tuple[list[Song], int]:
        if await self.is_navidrome():
            return await self.native.get_songs(sort, offset, size, starred, artist_id)
        if not starred:
            return [], 0  # every track: only Navidrome can list them
        songs = (await self._starred()).songs
        if artist_id:
            songs = [s for s in songs if s.artist_id == artist_id]
        ordered = sort_songs(songs, sort)
        return ordered[offset : offset + size], len(ordered)

    async def get_on_repeat(self, **kwargs: Any) -> list[Song]:
        if await self.is_navidrome():
            return await self.native.get_on_repeat(**kwargs)
        return []  # needs Navidrome's last play dates
