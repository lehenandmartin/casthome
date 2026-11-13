"""Navidrome's own REST API (the one its web UI uses).

The Subsonic API cannot list every track sorted by date added, play count…;
Navidrome's native `/api/song` endpoint can. It authenticates with a JWT
obtained from `/auth/login` with the same username and password, cached and
renewed when it expires.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

import httpx

from casthome.subsonic.client import (
    InvalidCredentialsError,
    NavidromeUnavailableError,
    NotAuthenticatedError,
    PasswordProvider,
)
from casthome.subsonic.formats import SUFFIX_MIME
from casthome.subsonic.models import Song

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

    async def get_songs(self, sort: SongSort = "recent", offset: int = 0, size: int = 100) -> tuple[list[Song], int]:
        field, order = SORTS[sort]
        r = await self._get(
            "/api/song", {"_start": offset, "_end": offset + size, "_sort": field, "_order": order, "missing": "false"}
        )
        items = [song_from_native(d) for d in r.json()]
        total = int(r.headers.get("x-total-count") or (offset + len(items)))
        return items, total
