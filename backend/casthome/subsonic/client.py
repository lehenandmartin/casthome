"""Async Subsonic/OpenSubsonic client for Navidrome."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Literal

import httpx

from casthome.subsonic.models import Album, Artist, Genre, Playlist, PlayQueue, SearchResult, Song
from casthome.subsonic.tokens import auth_params

log = logging.getLogger(__name__)

ERROR_WRONG_CREDENTIALS = 40


class SubsonicError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"Subsonic error {code}: {message}")
        self.code = code
        self.message = message


class InvalidCredentialsError(SubsonicError):
    pass


class NotAuthenticatedError(Exception):
    """No Navidrome password is stored yet."""


class NavidromeUnavailableError(Exception):
    pass


PasswordProvider = Callable[[], Awaitable[str | None]]
StarKind = Literal["song", "album", "artist"]


class SubsonicClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password_provider: PasswordProvider,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self._password_provider = password_provider
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        self._extensions: set[str] | None = None
        # Called when Navidrome rejects the stored password (it changed).
        self.on_invalid_credentials: Callable[[], Awaitable[None]] | None = None

    @property
    def http(self) -> httpx.AsyncClient:
        """Shared HTTP client (also used for Navidrome's native API)."""
        return self._http

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _password(self) -> str:
        password = await self._password_provider()
        if password is None:
            raise NotAuthenticatedError()
        return password

    async def call(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        password: str | None = None,
        post: bool = False,
    ) -> dict[str, Any]:
        pwd = password if password is not None else await self._password()
        query: dict[str, Any] = {**auth_params(self.username, pwd), "f": "json"}
        body = dict(params or {})
        # Note: httpx *replaces* a URL's query string when `params` is given,
        # so every parameter goes through `params` (or `data`), never the URL.
        url = f"{self.base_url}/rest/{endpoint}"
        try:
            if post:
                response = await self._http.post(url, params=query, data=body)
            else:
                response = await self._http.get(url, params={**query, **body})
        except httpx.HTTPError as exc:
            raise NavidromeUnavailableError(str(exc)) from exc
        if response.status_code >= 500:
            raise NavidromeUnavailableError(f"HTTP {response.status_code}")
        try:
            payload = response.json()["subsonic-response"]
        except (ValueError, KeyError) as exc:
            raise NavidromeUnavailableError("Invalid response from Navidrome") from exc
        if payload.get("status") != "ok":
            error = payload.get("error") or {}
            code = int(error.get("code", 0))
            message = str(error.get("message", "unknown error"))
            if code == ERROR_WRONG_CREDENTIALS:
                if password is None and self.on_invalid_credentials is not None:
                    await self.on_invalid_credentials()
                raise InvalidCredentialsError(code, message)
            raise SubsonicError(code, message)
        return payload

    # --- endpoints -----------------------------------------------------------

    async def ping(self, password: str | None = None) -> None:
        await self.call("ping", password=password)

    async def extensions(self) -> set[str]:
        if self._extensions is None:
            try:
                data = await self.call("getOpenSubsonicExtensions")
                self._extensions = {e["name"] for e in data.get("openSubsonicExtensions", [])}
            except SubsonicError:
                self._extensions = set()
        return self._extensions

    async def get_album_list(
        self, list_type: str, size: int = 50, offset: int = 0, genre: str | None = None
    ) -> list[Album]:
        params: dict[str, Any] = {"type": list_type, "size": size, "offset": offset}
        if genre is not None:
            params["genre"] = genre
        data = await self.call("getAlbumList2", params)
        return [Album.from_api(a) for a in (data.get("albumList2") or {}).get("album", [])]

    async def get_artists(self) -> list[Artist]:
        data = await self.call("getArtists")
        indexes = (data.get("artists") or {}).get("index", [])
        return [Artist.from_api(a) for index in indexes for a in index.get("artist", [])]

    async def get_artist(self, artist_id: str) -> tuple[Artist, list[Album]]:
        data = await self.call("getArtist", {"id": artist_id})
        raw = data["artist"]
        return Artist.from_api(raw), [Album.from_api(a) for a in raw.get("album", [])]

    async def get_genres(self) -> list[Genre]:
        data = await self.call("getGenres")
        return [Genre.from_api(g) for g in (data.get("genres") or {}).get("genre", [])]

    async def get_songs_by_genre(self, genre: str, count: int = 100, offset: int = 0) -> list[Song]:
        data = await self.call("getSongsByGenre", {"genre": genre, "count": count, "offset": offset})
        return [Song.from_api(s) for s in (data.get("songsByGenre") or {}).get("song", [])]

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        data = await self.call(
            "search3", {"query": query, "artistCount": limit, "albumCount": limit, "songCount": limit * 2}
        )
        return SearchResult.from_api(data.get("searchResult3"))

    # --- favorites & ratings -------------------------------------------------

    async def get_starred(self) -> SearchResult:
        data = await self.call("getStarred2")
        return SearchResult.from_api(data.get("starred2"))

    async def set_starred(self, kind: StarKind, item_id: str, starred: bool) -> None:
        param = {"song": "id", "album": "albumId", "artist": "artistId"}[kind]
        await self.call("star" if starred else "unstar", {param: item_id})

    async def set_rating(self, item_id: str, rating: int) -> None:
        await self.call("setRating", {"id": item_id, "rating": max(0, min(5, rating))})

    async def scrobble(self, song_id: str, submission: bool, time_ms: int | None = None) -> None:
        params: dict[str, Any] = {"id": song_id, "submission": "true" if submission else "false"}
        if time_ms is not None:
            params["time"] = time_ms
        await self.call("scrobble", params)

    # --- playlists -----------------------------------------------------------

    async def get_playlists(self) -> list[Playlist]:
        data = await self.call("getPlaylists")
        return [Playlist.from_api(p) for p in (data.get("playlists") or {}).get("playlist", [])]

    async def get_playlist(self, playlist_id: str) -> Playlist:
        data = await self.call("getPlaylist", {"id": playlist_id})
        return Playlist.from_api(data["playlist"])

    async def create_playlist(self, name: str, song_ids: list[str]) -> Playlist:
        data = await self.call("createPlaylist", {"name": name, "songId": song_ids}, post=await self._can_post())
        if "playlist" in data:
            return Playlist.from_api(data["playlist"])
        # Plain Subsonic servers return nothing: find the newest playlist with that name.
        matches = [p for p in await self.get_playlists() if p.name == name]
        if not matches:
            raise SubsonicError(0, "Playlist was not created")
        return max(matches, key=lambda p: p.changed or "")

    async def update_playlist(
        self,
        playlist_id: str,
        name: str | None = None,
        add_song_ids: list[str] | None = None,
        remove_indexes: list[int] | None = None,
    ) -> None:
        params: dict[str, Any] = {"playlistId": playlist_id}
        if name is not None:
            params["name"] = name
        if add_song_ids:
            params["songIdToAdd"] = add_song_ids
        if remove_indexes:
            params["songIndexToRemove"] = remove_indexes
        await self.call("updatePlaylist", params, post=await self._can_post())

    async def delete_playlist(self, playlist_id: str) -> None:
        await self.call("deletePlaylist", {"id": playlist_id})

    async def _can_post(self) -> bool:
        return "formPost" in await self.extensions()

    async def get_album(self, album_id: str) -> Album:
        data = await self.call("getAlbum", {"id": album_id})
        return Album.from_api(data["album"])

    async def get_song(self, song_id: str) -> Song:
        data = await self.call("getSong", {"id": song_id})
        return Song.from_api(data["song"])

    async def get_play_queue(self) -> PlayQueue:
        data = await self.call("getPlayQueue")
        return PlayQueue.from_api(data.get("playQueue"))

    async def save_play_queue(self, song_ids: list[str], current_id: str | None, position_ms: int) -> None:
        params: dict[str, Any] = {"id": song_ids}
        if current_id is not None:
            params["current"] = current_id
            params["position"] = max(0, position_ms)
        # Long queues do not fit in a URL: use a form POST when the server supports it.
        await self.call("savePlayQueue", params, post=await self._can_post())

    async def open_stream(
        self, song_id: str, fmt: str | None, max_bitrate: int, range_header: str | None
    ) -> httpx.Response:
        """Start streaming a song from Navidrome; the caller must close the response."""
        query: dict[str, Any] = {**auth_params(self.username, await self._password()), "id": song_id}
        if fmt:
            query["format"] = fmt
            query["estimateContentLength"] = "true"
        if max_bitrate > 0:
            query["maxBitRate"] = max_bitrate
        headers = {"Range": range_header} if range_header else {}
        request = self._http.build_request(
            "GET", f"{self.base_url}/rest/stream", params=query, headers=headers,
            timeout=httpx.Timeout(60.0, connect=5.0),
        )
        try:
            return await self._http.send(request, stream=True)
        except httpx.HTTPError as exc:
            raise NavidromeUnavailableError(str(exc)) from exc

    async def get_cover_art(self, cover_id: str, size: int | None) -> httpx.Response:
        query: dict[str, Any] = {**auth_params(self.username, await self._password()), "id": cover_id}
        if size:
            query["size"] = size
        try:
            response = await self._http.get(f"{self.base_url}/rest/getCoverArt", params=query)
        except httpx.HTTPError as exc:
            raise NavidromeUnavailableError(str(exc)) from exc
        return response
