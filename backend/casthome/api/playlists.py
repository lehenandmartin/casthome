"""Navidrome playlists: list, read, create, rename, edit, delete."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from casthome.api.deps import get_ctx, require_session

router = APIRouter(prefix="/api", tags=["playlists"], dependencies=[Depends(require_session)])


class CreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    song_ids: list[str] = Field(default_factory=list, max_length=5000)
    from_queue: bool = False  # "save the current queue as a playlist"

    @model_validator(mode="after")
    def _one_source(self) -> CreateBody:
        if self.from_queue and self.song_ids:
            raise ValueError("use either song_ids or from_queue")
        return self


class UpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    add_song_ids: list[str] = Field(default_factory=list, max_length=5000)
    remove_indexes: list[int] = Field(default_factory=list, max_length=5000)


@router.get("/playlists")
async def list_playlists(request: Request) -> list[dict]:
    items = await get_ctx(request).subsonic.get_playlists()
    return [p.model_dump(exclude={"songs"}) for p in items]


@router.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: str, request: Request) -> dict:
    return (await get_ctx(request).subsonic.get_playlist(playlist_id)).model_dump()


@router.post("/playlists", status_code=201)
async def create_playlist(body: CreateBody, request: Request) -> dict:
    ctx = get_ctx(request)
    song_ids = [e.item.id for e in ctx.coordinator.queue.entries] if body.from_queue else body.song_ids
    if body.from_queue and not song_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "nothing_to_play"})
    playlist = await ctx.subsonic.create_playlist(body.name.strip(), song_ids)
    return playlist.model_dump(exclude={"songs"})


@router.patch("/playlists/{playlist_id}", status_code=204)
async def update_playlist(playlist_id: str, body: UpdateBody, request: Request) -> None:
    await get_ctx(request).subsonic.update_playlist(
        playlist_id,
        name=body.name.strip() if body.name else None,
        add_song_ids=body.add_song_ids,
        remove_indexes=sorted(set(body.remove_indexes)),
    )


@router.delete("/playlists/{playlist_id}", status_code=204)
async def delete_playlist(playlist_id: str, request: Request) -> None:
    await get_ctx(request).subsonic.delete_playlist(playlist_id)
