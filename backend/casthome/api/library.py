"""Read-only library browsing, proxied from Navidrome (no local index)."""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from casthome.api.deps import get_ctx, require_session
from casthome.subsonic.client import NavidromeUnavailableError, SubsonicError
from casthome.subsonic.models import Artist, Song
from casthome.subsonic.native import SongSort

router = APIRouter(prefix="/api", tags=["library"], dependencies=[Depends(require_session)])

AlbumListType = Literal["newest", "recent", "random", "frequent", "alphabeticalByName", "starred", "byGenre"]


@router.get("/library/albums")
async def albums(
    request: Request,
    type: AlbumListType = "newest",  # noqa: A002 - mirrors the Subsonic parameter
    size: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
    genre: str | None = Query(None, max_length=200),
    starred: bool = False,
) -> list[dict]:
    if type == "byGenre" and not genre:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "genre_required"})
    ctx = get_ctx(request)
    if starred:
        # Favorites with the chosen sort: Subsonic's "starred" list cannot be sorted.
        items = await ctx.library.get_albums(type, offset, size, starred=True)
    else:
        items = await ctx.subsonic.get_album_list(type, size, offset, genre if type == "byGenre" else None)
    return [a.model_dump(exclude={"songs"}) for a in items]


@router.get("/library/songs")
async def songs(
    request: Request,
    sort: SongSort = "recent",
    offset: int = Query(0, ge=0),
    size: int = Query(100, ge=1, le=500),
    starred: bool = False,
    artist_id: str | None = Query(None, max_length=200),
) -> dict:
    """Every track (or only favorites, or one artist's), paged; "recent" = most recently added first."""
    items, total = await get_ctx(request).library.get_songs(sort, offset, size, starred, artist_id)
    return {"items": [s.model_dump() for s in items], "total": total}


@router.get("/library/albums/{album_id}")
async def album(album_id: str, request: Request) -> dict:
    return (await get_ctx(request).subsonic.get_album(album_id)).model_dump()


@router.get("/library/artists")
async def artists(request: Request) -> list[dict]:
    items = await get_ctx(request).subsonic.get_artists()
    return [a.model_dump() for a in items]


@router.get("/library/artists/{artist_id}")
async def artist(artist_id: str, request: Request) -> dict:
    info, albums_ = await get_ctx(request).subsonic.get_artist(artist_id)
    return {**info.model_dump(), "albums": [a.model_dump(exclude={"songs"}) for a in albums_]}


TOP_SONGS = 10


@router.get("/library/artists/{artist_id}/highlights")
async def artist_highlights(artist_id: str, request: Request) -> dict:
    """Popular tracks and the number of favorite tracks, for the artist page.

    Popular tracks come from Navidrome's getTopSongs (Last.fm popularity,
    matched to the library); without them, the artist's most played tracks.
    """
    ctx = get_ctx(request)
    info, _albums = await ctx.subsonic.get_artist(artist_id)

    async def popular() -> tuple[str, list]:
        try:
            top = await ctx.subsonic.get_top_songs(info.name, TOP_SONGS)
        except SubsonicError:
            top = []
        if top:
            return "popular", top
        played, _total = await ctx.library.get_songs("frequent", 0, TOP_SONGS, artist_id=artist_id)
        return "most_played", [s for s in played if s.play_count]

    (source, top), (_liked, liked_count) = await asyncio.gather(
        popular(), ctx.library.get_songs("recent", 0, 1, starred=True, artist_id=artist_id)
    )
    return {"top_source": source, "top": [s.model_dump() for s in top], "liked_count": liked_count}


SIMILAR_ARTISTS = 18


def includes_artist(name: str, candidate: str) -> bool:
    """`candidate` names the artist, alone or with others ("Madonna & Charli xcx")."""
    return re.search(rf"(?<!\w){re.escape(name)}(?!\w)", candidate, re.IGNORECASE) is not None


def pick_similar_artists(
    artist: Artist,
    lastfm: list[Artist],
    similar_songs: list[Song],
    library: dict[str, Artist],
    limit: int = SIMILAR_ARTISTS,
) -> list[Artist]:
    """Last.fm's similar artists first, then the artists most present among
    similar tracks. Never the artist again, a duo with them, or an artist
    without albums in the library (an empty page)."""
    by_count = Counter(s.artist_id for s in similar_songs if s.artist_id)
    from_songs = [library[i] for i, _n in by_count.most_common() if i in library]
    picked: list[Artist] = []
    seen = {artist.id}
    for candidate in [*lastfm, *from_songs]:
        if (
            candidate.id in seen
            or candidate.album_count == 0
            or includes_artist(artist.name, candidate.name)
        ):
            continue
        seen.add(candidate.id)
        picked.append(library.get(candidate.id, candidate))
        if len(picked) == limit:
            break
    return picked


@router.get("/library/artists/{artist_id}/similar")
async def similar_artists(artist_id: str, request: Request) -> list[dict]:
    """Similar artists in the library, for the bottom of the artist page."""
    ctx = get_ctx(request)

    async def optional(call):  # type: ignore[no-untyped-def]
        try:
            return await call
        except (SubsonicError, NavidromeUnavailableError):
            return []

    (info, _albums), lastfm, songs, library = await asyncio.gather(
        ctx.subsonic.get_artist(artist_id),
        optional(ctx.subsonic.get_similar_artists(artist_id)),
        optional(ctx.subsonic.get_similar_songs2(artist_id, 100)),
        ctx.subsonic.get_artists(),
    )
    picked = pick_similar_artists(info, lastfm, songs, {a.id: a for a in library})
    return [a.model_dump() for a in picked]


@router.get("/library/genres")
async def genres(request: Request) -> list[dict]:
    items = await get_ctx(request).subsonic.get_genres()
    return [g.model_dump() for g in sorted(items, key=lambda g: g.name.lower())]


@router.get("/library/genres/{genre}/songs")
async def genre_songs(
    genre: str,
    request: Request,
    count: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    items = await get_ctx(request).subsonic.get_songs_by_genre(genre, count, offset)
    return [s.model_dump() for s in items]


@router.get("/library/search")
async def search(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    return (await get_ctx(request).subsonic.search(q, limit)).model_dump()


class StarBody(BaseModel):
    kind: Literal["song", "album", "artist"]
    id: str
    starred: bool


class RatingBody(BaseModel):
    id: str
    rating: int = Field(ge=0, le=5)  # 0 removes the rating


@router.get("/library/starred")
async def starred(request: Request) -> dict:
    return (await get_ctx(request).subsonic.get_starred()).model_dump()


@router.put("/library/star", status_code=204)
async def set_star(body: StarBody, request: Request) -> None:
    ctx = get_ctx(request)
    await ctx.subsonic.set_starred(body.kind, body.id, body.starred)
    ctx.starred_memo.forget()  # the Home page counts favourites
    if body.kind == "song":
        ctx.coordinator.update_song_flags(body.id, starred=body.starred)


@router.put("/library/rating", status_code=204)
async def set_rating(body: RatingBody, request: Request) -> None:
    ctx = get_ctx(request)
    await ctx.subsonic.set_rating(body.id, body.rating)
    ctx.coordinator.update_song_flags(body.id, user_rating=body.rating)


@router.get("/cover/{cover_id}")
async def cover(cover_id: str, request: Request, size: int = Query(300, ge=32, le=1200)) -> Response:
    """Cover art for the browser, converted to WebP (JPEG for a browser without
    WebP) and kept on disk, see covers.py; Navidrome credentials never reach the
    frontend."""
    ctx = get_ctx(request)

    async def fetch() -> tuple[bytes, str] | None:
        upstream = await ctx.subsonic.get_cover_art(cover_id, size)
        content_type = upstream.headers.get("content-type", "")
        if upstream.status_code != 200 or not content_type.startswith("image/"):
            return None
        return upstream.content, content_type

    webp = "image/webp" in request.headers.get("accept", "")
    found = await ctx.covers.get(cover_id, size, webp, fetch)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "cover_not_found"})
    return Response(
        content=found.data,
        media_type=found.content_type,
        headers={"Cache-Control": "private, max-age=604800", "Vary": "Accept"},
    )
