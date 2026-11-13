"""Playback, device and queue commands. Results are pushed over the WebSocket."""

from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from casthome.api.deps import get_ctx, require_session
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
    index: int = Field(ge=0)


class QueueAddBody(BaseModel):
    album_id: str | None = None
    song_ids: list[str] | None = Field(default=None, max_length=2000)
    mode: AddMode = AddMode.NOW
    start_index: int = Field(default=0, ge=0)
    replace: bool = True  # with mode=now: replace the whole queue (play album)

    @model_validator(mode="after")
    def _one_source(self) -> QueueAddBody:
        if (self.album_id is None) == (self.song_ids is None):
            raise ValueError("exactly one of album_id or song_ids is required")
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
    if ctx.cast.get(body.uuid) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "device_not_found"})
    await ctx.coordinator.select_device(body.uuid)


@router.post("/player/seek", status_code=204)
async def seek(body: SeekBody, request: Request) -> None:
    await get_ctx(request).coordinator.seek(body.position)


@router.post("/player/jump", status_code=204)
async def jump(body: JumpBody, request: Request) -> None:
    await get_ctx(request).coordinator.jump(body.index)


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
    if body.album_id is not None:
        album = await ctx.subsonic.get_album(body.album_id)
        songs = album.songs or []
    else:
        songs = list(await asyncio.gather(*(ctx.subsonic.get_song(i) for i in body.song_ids or [])))
    if not songs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "nothing_to_play"})
    if body.mode == AddMode.NOW and body.replace:
        await ctx.coordinator.play_songs(songs, body.start_index)
    else:
        await ctx.coordinator.add_songs(songs, body.mode)


@router.delete("/queue", status_code=204)
async def clear_queue(request: Request) -> None:
    await get_ctx(request).coordinator.clear()


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
