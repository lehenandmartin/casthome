"""Read-only library browsing, proxied from Navidrome (no local index)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from casthome.api.deps import get_ctx, require_session

router = APIRouter(prefix="/api", tags=["library"], dependencies=[Depends(require_session)])

AlbumListType = Literal["newest", "recent", "random", "frequent", "alphabeticalByName", "starred"]


@router.get("/library/albums")
async def albums(
    request: Request,
    type: AlbumListType = "newest",  # noqa: A002 - mirrors the Subsonic parameter
    size: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    items = await get_ctx(request).subsonic.get_album_list(type, size, offset)
    return [a.model_dump(exclude={"songs"}) for a in items]


@router.get("/library/albums/{album_id}")
async def album(album_id: str, request: Request) -> dict:
    return (await get_ctx(request).subsonic.get_album(album_id)).model_dump()


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
