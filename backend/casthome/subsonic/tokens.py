"""Subsonic token authentication and URL building (pure functions)."""

from __future__ import annotations

import hashlib
import secrets
from urllib.parse import urlencode

API_VERSION = "1.16.1"
CLIENT_NAME = "CastHome"


def make_token(password: str, salt: str) -> str:
    return hashlib.md5((password + salt).encode()).hexdigest()


def auth_params(username: str, password: str, salt: str | None = None) -> dict[str, str]:
    salt = salt or secrets.token_hex(8)
    return {
        "u": username,
        "t": make_token(password, salt),
        "s": salt,
        "v": API_VERSION,
        "c": CLIENT_NAME,
    }


def build_url(base_url: str, endpoint: str, params: dict[str, str | int]) -> str:
    return f"{base_url.rstrip('/')}/rest/{endpoint}?{urlencode(params)}"


def stream_url(
    base_url: str,
    username: str,
    password: str,
    song_id: str,
    fmt: str | None = None,
    max_bitrate: int = 0,
    salt: str | None = None,
) -> str:
    """URL fetched by the Cast device itself: base_url must be reachable from it."""
    params: dict[str, str | int] = {"id": song_id, **auth_params(username, password, salt)}
    if fmt:
        params["format"] = fmt
        # Lets Navidrome send a Content-Length so the receiver can show duration and seek.
        params["estimateContentLength"] = "true"
    if max_bitrate > 0:
        params["maxBitRate"] = max_bitrate
    return build_url(base_url, "stream", params)


def cover_art_url(
    base_url: str, username: str, password: str, cover_id: str, size: int = 600, salt: str | None = None
) -> str:
    params: dict[str, str | int] = {"id": cover_id, "size": size, **auth_params(username, password, salt)}
    return build_url(base_url, "getCoverArt", params)
