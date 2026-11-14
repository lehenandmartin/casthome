"""Navidrome's own REST API (the one its web UI uses).

The Subsonic API cannot list every track sorted by date added, play count…;
Navidrome's native `/api/song` endpoint can. It authenticates with a JWT
obtained from `/auth/login` with the same username and password, cached and
renewed when it expires.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx

from casthome.subsonic.client import (
    InvalidCredentialsError,
    NavidromeUnavailableError,
    NotAuthenticatedError,
    PasswordProvider,
)
from casthome.subsonic.formats import SUFFIX_MIME
from casthome.subsonic.models import Album, Song

SongSort = Literal["recent", "title", "artist", "album", "frequent", "played"]

# CastHome sort -> (Navidrome field, order)
SORTS: dict[str, tuple[str, str]] = {
    "recent": ("createdAt", "DESC"),
    "title": ("title", "ASC"),
    "artist": ("artist", "ASC"),
    "album": ("album", "ASC"),
    "frequent": ("playCount", "DESC"),
    "played": ("playDate", "DESC"),
}


# Album list types (as in Subsonic getAlbumList2) -> Navidrome sort for /api/album
ALBUM_SORTS: dict[str, tuple[str, str]] = {
    "newest": ("createdAt", "DESC"),
    "recent": ("playDate", "DESC"),
    "frequent": ("playCount", "DESC"),
    "alphabeticalByName": ("name", "ASC"),
    "random": ("random", "ASC"),
}


def album_from_native(d: dict[str, Any]) -> Album:
    album_id = str(d["id"])
    return Album(
        id=album_id,
        name=d.get("name", ""),
        artist=d.get("albumArtist") or d.get("artist") or "",
        artist_id=d.get("albumArtistId") or d.get("artistId"),
        cover_art=f"al-{album_id}",
        year=d.get("maxYear") or None,
        song_count=int(d.get("songCount") or 0),
        duration=float(d.get("duration") or 0),
        starred=bool(d.get("starred")),
        user_rating=int(d.get("rating") or 0),
        play_count=int(d.get("playCount") or 0),
    )


def song_from_native(d: dict[str, Any]) -> Song:
    suffix = (d.get("suffix") or "").lower()
    song_id = str(d["id"])
    album_id = d.get("albumId")
    # Same cover ids the Subsonic API hands out: the track's own art, else its album's.
    cover = f"mf-{song_id}" if d.get("hasCoverArt") else (f"al-{album_id}" if album_id else None)
    return Song(
        id=song_id,
        title=d.get("title", ""),
        artist=d.get("artist", ""),
        artist_id=d.get("artistId"),
        album=d.get("album", ""),
        album_id=album_id,
        cover_art=cover,
        duration=float(d.get("duration") or 0),
        track=d.get("trackNumber") or None,
        disc=d.get("discNumber") or None,
        suffix=suffix,
        content_type=SUFFIX_MIME.get(suffix, ""),
        bit_rate=d.get("bitRate"),
        sampling_rate=d.get("sampleRate"),
        bit_depth=d.get("bitDepth") or None,
        starred=bool(d.get("starred")),
        user_rating=int(d.get("rating") or 0),
    )


class NativeClient:
    def __init__(self, base_url: str, username: str, password_provider: PasswordProvider, http: httpx.AsyncClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self._password_provider = password_provider
        self._http = http
        self._token: str | None = None
        self._lock = asyncio.Lock()
        # Called when Navidrome refuses the password (see SubsonicClient).
        self.on_rejected: Callable[[], None] | None = None

    def configure(self, base_url: str, username: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self._token = None

    async def _login(self) -> str:
        password = await self._password_provider()
        if password is None:
            raise NotAuthenticatedError()
        try:
            r = await self._http.post(
                f"{self.base_url}/auth/login", json={"username": self.username, "password": password}
            )
        except httpx.HTTPError as exc:
            raise NavidromeUnavailableError(str(exc)) from exc
        if r.status_code == 401:
            if self.on_rejected is not None:
                self.on_rejected()
            raise InvalidCredentialsError(40, "Navidrome refused the stored password")
        if r.status_code >= 400:
            raise NavidromeUnavailableError(f"HTTP {r.status_code} from /auth/login")
        return str(r.json()["token"])

    async def _get(self, path: str, params: dict[str, Any]) -> httpx.Response:
        for attempt in range(2):
            async with self._lock:
                if self._token is None:
                    self._token = await self._login()
                token = self._token
            try:
                r = await self._http.get(
                    f"{self.base_url}{path}", params=params, headers={"X-ND-Authorization": f"Bearer {token}"}
                )
            except httpx.HTTPError as exc:
                raise NavidromeUnavailableError(str(exc)) from exc
            if r.status_code == 401 and attempt == 0:
                self._token = None  # expired: log in again once
                continue
            if r.status_code >= 400:
                raise NavidromeUnavailableError(f"HTTP {r.status_code} from {path}")
            return r
        raise NavidromeUnavailableError(f"Not authorized for {path}")

    async def get_albums(
        self, list_type: str = "newest", offset: int = 0, size: int = 40, starred: bool = False
    ) -> list[Album]:
        """Albums with Navidrome's own filters (used for the favorites filter)."""
        field, order = ALBUM_SORTS.get(list_type, ALBUM_SORTS["newest"])
        params: dict[str, Any] = {"_start": offset, "_end": offset + size, "_sort": field, "_order": order}
        if starred:
            params["starred"] = "true"
        r = await self._get("/api/album", params)
        return [album_from_native(d) for d in r.json()]

    async def get_on_repeat(self, days: int = 30, limit: int = 5, max_scan: int = 1000) -> list[Song]:
        """Most played tracks among those played in the last `days` days.

        Navidrome keeps a total play count and the last play date per track,
        not a history: tracks are filtered on their last play date, then
        ranked by their total count.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        recent: list[dict[str, Any]] = []
        start, page_size = 0, 200
        while start < max_scan:
            r = await self._get(
                "/api/song", {"_start": start, "_end": start + page_size, "_sort": "playDate", "_order": "DESC"}
            )
            page = r.json()
            if not page:
                break
            for row in page:
                played = _parse_date(row.get("playDate"))
                if played is None or played < cutoff:
                    page = []  # sorted by play date: everything after is older
                    break
                recent.append(row)
            if len(page) < page_size:
                break
            start += page_size
        recent.sort(key=lambda row: int(row.get("playCount") or 0), reverse=True)
        return [song_from_native(row) for row in recent[:limit]]

    async def get_songs(
        self,
        sort: SongSort = "recent",
        offset: int = 0,
        size: int = 100,
        starred: bool = False,
        artist_id: str | None = None,
    ) -> tuple[list[Song], int]:
        """Tracks, paged. `artist_id` keeps the artist's tracks, features included."""
        field, order = SORTS[sort]
        params: dict[str, Any] = {"_start": offset, "_end": offset + size, "_sort": field, "_order": order, "missing": "false"}
        if starred:
            params["starred"] = "true"
        if artist_id:
            params["artists_id"] = artist_id
        r = await self._get("/api/song", params)
        items = [song_from_native(d) for d in r.json()]
        total = int(r.headers.get("x-total-count") or (offset + len(items)))
        return items, total


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
