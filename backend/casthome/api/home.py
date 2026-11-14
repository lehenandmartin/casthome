"""Home page data, gathered in one request.

Every section is fetched in parallel and independently: one failing (say,
Navidrome's native API) leaves that row empty instead of breaking the page.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, Request

from casthome.api.deps import get_ctx, require_session
from casthome.subsonic.models import Album, Artist

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["home"], dependencies=[Depends(require_session)])

ROW = 12
T = TypeVar("T")


async def _safe(name: str, coro: Awaitable[T], default: T) -> T:
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - a broken row must not break the page
        log.warning("Home section %s unavailable: %s", name, exc)
        return default


def artists_from_albums(albums: list[Album], limit: int) -> list[Artist]:
    """Fallback for "favorite artists": the artists of the most played albums."""
    seen: set[str] = set()
    out: list[Artist] = []
    for album in albums:
        if album.artist_id and album.artist_id not in seen:
            seen.add(album.artist_id)
            out.append(Artist(id=album.artist_id, name=album.artist, cover_art=f"ar-{album.artist_id}"))
        if len(out) >= limit:
            break
    return out


@router.get("/home")
async def home(request: Request) -> dict[str, Any]:
    ctx = get_ctx(request)
    sub = ctx.subsonic
    recent_played, recent_added, starred, on_repeat, playlists, frequent = await asyncio.gather(
        _safe("recently played", sub.get_album_list("recent", ROW), []),
        _safe("recently added", sub.get_album_list("newest", ROW), []),
        _safe("favorites", sub.get_starred(), None),
        _safe("on repeat", ctx.native.get_on_repeat(days=30, limit=5), []),
        _safe("playlists", sub.get_playlists(), []),
        _safe("most played", sub.get_album_list("frequent", 40), []),
    )
    favorite_artists = [
        a if a.cover_art else a.model_copy(update={"cover_art": f"ar-{a.id}"}) for a in (starred.artists if starred else [])
    ]
    artists_are_favorites = bool(favorite_artists)
    if not favorite_artists:
        favorite_artists = artists_from_albums(frequent, ROW)
    recent_playlists = sorted(playlists, key=lambda p: p.changed or "", reverse=True)[:ROW]
    return {
        "recently_played": [a.model_dump(exclude={"songs"}) for a in recent_played],
        "recently_added": [a.model_dump(exclude={"songs"}) for a in recent_added],
        "favorite_artists": [a.model_dump() for a in favorite_artists[:ROW]],
        "artists_are_favorites": artists_are_favorites,
        "favorite_song_count": len(starred.songs) if starred else 0,
        "on_repeat": [s.model_dump() for s in on_repeat],
        "playlists": [p.model_dump(exclude={"songs"}) for p in recent_playlists],
    }
