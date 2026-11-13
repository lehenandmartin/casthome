"""Read-only library browsing, proxied from Navidrome (no local index)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from casthome.api.deps import get_ctx, require_session

router = APIRouter(prefix="/api", tags=["library"], dependencies=[Depends(require_session)])

AlbumListType = Literal["newest", "recent", "random", "frequent", "alphabeticalByName", "starred", "byGenre"]


@router.get("/library/albums")
async def albums(
    request: Request,
    type: AlbumListType = "newest",  # noqa: A002 - mirrors the Subsonic parameter
    size: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
    genre: str | None = Query(None, max_length=200),
) -> list[dict]:
    if type == "byGenre" and not genre:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "genre_required"})
    items = await get_ctx(request).subsonic.get_album_list(type, size, offset, genre if type == "byGenre" else None)
    return [a.model_dump(exclude={"songs"}) for a in items]


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
    if body.kind == "song":
        ctx.coordinator.update_song_flags(body.id, starred=body.starred)


@router.put("/library/rating", status_code=204)
async def set_rating(body: RatingBody, request: Request) -> None:
    ctx = get_ctx(request)
    await ctx.subsonic.set_rating(body.id, body.rating)
    ctx.coordinator.update_song_flags(body.id, user_rating=body.rating)


@router.get("/cover/{cover_id}")
async def cover(cover_id: str, request: Request, size: int = Query(300, ge=32, le=1200)) -> Response:
    """Cover art for the browser; Navidrome credentials never reach the frontend."""
    upstream = await get_ctx(request).subsonic.get_cover_art(cover_id, size)
    if upstream.status_code != 200 or not upstream.headers.get("content-type", "").startswith("image/"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "cover_not_found"})
    return Response(
        content=upstream.content,
        media_type=upstream.headers["content-type"],
        headers={"Cache-Control": "private, max-age=604800"},
    )
