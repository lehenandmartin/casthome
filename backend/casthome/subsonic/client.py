"""Async Subsonic/OpenSubsonic client for Navidrome."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from casthome.subsonic.models import Album, PlayQueue, Song
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

    async def get_album_list(self, list_type: str, size: int = 50, offset: int = 0) -> list[Album]:
        data = await self.call("getAlbumList2", {"type": list_type, "size": size, "offset": offset})
        return [Album.from_api(a) for a in (data.get("albumList2") or {}).get("album", [])]

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
        use_post = "formPost" in await self.extensions()
        await self.call("savePlayQueue", params, post=use_post)

    async def get_cover_art(self, cover_id: str, size: int | None) -> httpx.Response:
        query: dict[str, Any] = {**auth_params(self.username, await self._password()), "id": cover_id}
        if size:
            query["size"] = size
        try:
            response = await self._http.get(f"{self.base_url}/rest/getCoverArt", params=query)
        except httpx.HTTPError as exc:
            raise NavidromeUnavailableError(str(exc)) from exc
        return response
