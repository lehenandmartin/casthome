"""Playback, device and queue commands. Results are pushed over the WebSocket."""

from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from casthome.api.deps import get_ctx, require_session
from casthome.cast.browser import client_id_of
from casthome.queue.logic import AddMode, RepeatMode

router = APIRouter(prefix="/api", tags=["player"], dependencies=[Depends(require_session)])


class DeviceBody(BaseModel):
    uuid: str


class SeekBody(BaseModel):
    position: float = Field(ge=0)


class ModeBody(BaseModel):
    shuffle: bool | None = None
    repeat: RepeatMode | None = None


class VolumeBody(BaseModel):
    level: float | None = Field(default=None, ge=0, le=1)
    muted: bool | None = None


class JumpBody(BaseModel):
    index: int | None = Field(default=None, ge=0)
    uid: int | None = None  # preferred: stable even if the queue changed meanwhile


class MoveBody(BaseModel):
    uid: int
    to_index: int = Field(ge=0)
    queued: bool | None = None  # move into (true) / out of (false) "next in queue"


class QueueAddBody(BaseModel):
    album_id: str | None = None
    artist_id: str | None = None
    playlist_id: str | None = None
    song_ids: list[str] | None = Field(default=None, max_length=2000)
    mode: AddMode = AddMode.NOW
    start_index: int = Field(default=0, ge=0)
    replace: bool = True  # with mode=now: replace the whole queue (play album)

    @model_validator(mode="after")
    def _one_source(self) -> QueueAddBody:
        sources = [self.album_id, self.artist_id, self.playlist_id, self.song_ids]
        if sum(source is not None for source in sources) != 1:
            raise ValueError("exactly one of album_id, artist_id, playlist_id or song_ids is required")
        return self


@router.get("/state")
async def state(request: Request) -> dict:
    return get_ctx(request).full_snapshot()


@router.get("/devices")
async def devices(request: Request) -> list[dict]:
    return get_ctx(request).devices_snapshot()


@router.put("/player/device", status_code=204)
async def select_device(body: DeviceBody, request: Request) -> None:
    ctx = get_ctx(request)
    client_id = client_id_of(body.uuid)
    known = ctx.hub.has_client(client_id) if client_id is not None else ctx.cast.get(body.uuid) is not None
    if not known:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "device_not_found"})
    await ctx.coordinator.select_device(body.uuid)


@router.post("/player/seek", status_code=204)
async def seek(body: SeekBody, request: Request) -> None:
    await get_ctx(request).coordinator.seek(body.position)


@router.post("/player/jump", status_code=204)
async def jump(body: JumpBody, request: Request) -> None:
    c = get_ctx(request).coordinator
    if body.uid is not None:
        await c.jump_uid(body.uid)
    elif body.index is not None:
        await c.jump(body.index)
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "invalid_queue_index"})


@router.put("/player/mode", status_code=204)
async def set_mode(body: ModeBody, request: Request) -> None:
    await get_ctx(request).coordinator.set_mode(shuffle=body.shuffle, repeat=body.repeat)


@router.put("/player/volume", status_code=204)
async def set_volume(body: VolumeBody, request: Request) -> None:
    c = get_ctx(request).coordinator
    if body.level is not None:
        await c.set_volume(body.level)
    if body.muted is not None:
        await c.set_muted(body.muted)


@router.post("/queue", status_code=204)
async def add_to_queue(body: QueueAddBody, request: Request) -> None:
    ctx = get_ctx(request)
    context_name: str | None = None  # shown as "Next from: <name>"
    if body.album_id is not None:
        album = await ctx.subsonic.get_album(body.album_id)
        songs = album.songs or []
        context_name = album.name
    elif body.playlist_id is not None:
        playlist = await ctx.subsonic.get_playlist(body.playlist_id)
        songs = playlist.songs or []
        context_name = playlist.name
    elif body.artist_id is not None:
        artist, artist_albums = await ctx.subsonic.get_artist(body.artist_id)
        full = await asyncio.gather(*(ctx.subsonic.get_album(a.id) for a in artist_albums))
        songs = [song for a in full for song in (a.songs or [])]
        context_name = artist.name
    else:
        songs = list(await asyncio.gather(*(ctx.subsonic.get_song(i) for i in body.song_ids or [])))
    if not songs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "nothing_to_play"})
    if body.mode == AddMode.NOW and body.replace:
        await ctx.coordinator.play_songs(songs, body.start_index, context_name)
    else:
        await ctx.coordinator.add_songs(songs, body.mode)


@router.delete("/queue/items/{uid}", status_code=204)
async def remove_queue_item(uid: int, request: Request) -> None:
    await get_ctx(request).coordinator.remove_entry(uid)


@router.post("/queue/move", status_code=204)
async def move_queue_item(body: MoveBody, request: Request) -> None:
    await get_ctx(request).coordinator.move_entry(body.uid, body.to_index, body.queued)


@router.delete("/queue", status_code=204)
async def clear_queue(request: Request, queued_only: bool = False) -> None:
    """queued_only=true empties "next in queue" only (Spotify's "Clear queue")."""
    c = get_ctx(request).coordinator
    if queued_only:
        await c.clear_queued()
    else:
        await c.clear()


# Declared last so /player/seek and /player/jump are matched first.
Action = Literal["play", "pause", "toggle", "next", "previous", "stop"]


@router.post("/player/{action}", status_code=204)
async def player_action(action: Action, request: Request) -> None:
    c = get_ctx(request).coordinator
    handlers = {
        "play": c.play,
        "pause": c.pause,
        "toggle": c.toggle,
        "next": c.next,
        "previous": c.previous,
        "stop": c.stop_playback,
    }
    await handlers[action]()
