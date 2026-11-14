"""Settings saved from the browser: the Navidrome connection and access to CastHome."""

from __future__ import annotations

import asyncio
import ipaddress
import re
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from casthome.api.auth import throttle, throttle_passed
from casthome.api.deps import OPEN_SESSION, client_host, get_ctx, require_session, start_session
from casthome.appconfig import AccessMode, NavidromeConfig, PlaybackConfig, is_local_address
from casthome.auth.sessions import Session
from casthome.config import check_cast_url, normalize_url
from casthome.context import AppContext
from casthome.subsonic.client import (
    InvalidCredentialsError,
    NavidromeUnavailableError,
    SubsonicClient,
    SubsonicError,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])

PASSWORD_MIN = 4


class NavidromeBody(BaseModel):
    url: str = Field(default="", max_length=2048)
    # Blank: same as `url`.
    public_url: str = Field(default="", max_length=2048)
    username: str = Field(default="", max_length=256)
    # Blank keeps the saved password (same server and account only).
    password: str | None = Field(default=None, max_length=1024)


STREAM_FORMATS = ("raw", "mp3", "aac", "opus")
BITRATES = (0, 96, 128, 160, 192, 256, 320)
HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")


class PlaybackBody(BaseModel):
    stream_format: str = "raw"
    max_bitrate: int = 0
    preload_next: bool = True
    known_hosts: list[str] = Field(default_factory=list, max_length=32)
    scrobble: bool = True


class AccessBody(BaseModel):
    mode: AccessMode
    # New CastHome password; optional when one is already set.
    password: str | None = Field(default=None, max_length=1024)
    # Required to change anything once a password is set.
    current_password: str | None = Field(default=None, max_length=1024)
    # For a new session created by this change.
    remember: bool = True


def _bad(code: str, **params: Any) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": code, "params": params})


async def resolve_navidrome(ctx: AppContext, body: NavidromeBody) -> tuple[NavidromeConfig, str]:
    """Validate a Navidrome form against the locked (environment) values and
    check it against the server. Returns the config and the password to use."""
    locked = set(ctx.config.locked)
    current = ctx.config.navidrome_fields()
    raw = {
        "url": current["url"] if "url" in locked else body.url,
        "public_url": current["public_url"] if "public_url" in locked else body.public_url,
        "username": current["username"] if "username" in locked else body.username.strip(),
    }
    try:
        url = normalize_url(raw["url"])
    except ValueError:
        raise _bad("invalid_url", field="url") from None
    try:
        public_url = check_cast_url(normalize_url(raw["public_url"] or url))
    except ValueError:
        raise _bad("cast_url_local" if raw["public_url"] or url else "invalid_url", field="public_url") from None
    username = raw["username"]
    if not username:
        raise _bad("username_required")

    if ctx.config.env_password:
        password: str | None = ctx.config.env_password
    elif body.password:
        password = body.password
    elif ctx.config.navidrome is not None and (url, username) == (ctx.config.navidrome.url, ctx.config.navidrome.username):
        # Never send the saved password to another server or account.
        password = await ctx.credentials.get_password()
    else:
        password = None
    if not password:
        raise _bad("password_required")

    async def given() -> str | None:
        return password

    probe = SubsonicClient(url, username, given, http=ctx.subsonic.http)
    try:
        await probe.ping(password=password)
    except InvalidCredentialsError:
        raise _bad("navidrome_rejected_credentials") from None
    except NavidromeUnavailableError:
        raise _bad("navidrome_unreachable", url=url) from None
    except SubsonicError as exc:
        raise _bad("navidrome_error", message=exc.message) from None
    return NavidromeConfig(url=url, public_url=public_url, username=username), password


async def save_navidrome(ctx: AppContext, config: NavidromeConfig, password: str, reload_queue: bool = False) -> None:
    previous = ctx.config.navidrome
    await ctx.config.save_navidrome(config)
    if not ctx.config.env_password:
        await ctx.credentials.set_password(password)
    ctx.apply_navidrome()
    ctx.hub.publish("server", ctx.server_snapshot)
    if reload_queue or previous is None or (previous.url, previous.username) != (config.url, config.username):
        # Another library: load its play queue.
        asyncio.create_task(ctx.coordinator.restore())


def validate_new_access(ctx: AppContext, body: AccessBody) -> None:
    if body.mode is AccessMode.OPEN:
        return
    if body.password is None and not ctx.config.has_password:
        raise _bad("password_required")
    if body.password is not None and len(body.password) < PASSWORD_MIN:
        raise _bad("password_too_short", min=PASSWORD_MIN)


@router.get("")
async def get_settings(request: Request, _session: Annotated[Session, Depends(require_session)]) -> dict:
    ctx = get_ctx(request)
    return {
        "navidrome": {**ctx.config.navidrome_fields(), "has_password": await ctx.credentials.get_password() is not None},
        "locked": ctx.config.locked,
        "access": {"mode": ctx.config.access_mode, "has_password": ctx.config.has_password},
        "playback": {**asdict(ctx.config.playback), "locked": ctx.config.playback_locked},
        # Whether LAN mode would let this browser in without a password.
        "client_is_local": is_local_address(client_host(request)),
    }


@router.post("/navidrome/test")
async def test_navidrome(
    body: NavidromeBody, request: Request, _session: Annotated[Session, Depends(require_session)]
) -> dict:
    await resolve_navidrome(get_ctx(request), body)
    return {"ok": True}


@router.put("/navidrome")
async def update_navidrome(
    body: NavidromeBody, request: Request, _session: Annotated[Session, Depends(require_session)]
) -> dict:
    ctx = get_ctx(request)
    config, password = await resolve_navidrome(ctx, body)
    await save_navidrome(ctx, config, password)
    return {"ok": True}


@router.put("/access")
async def update_access(
    body: AccessBody,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(require_session)],
) -> dict:
    ctx = get_ctx(request)
    if ctx.config.has_password:
        ip = client_host(request) or ""
        throttle(ip)
        if not body.current_password or not await ctx.config.check_password(body.current_password):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "invalid_credentials"})
        throttle_passed(ip)
    validate_new_access(ctx, body)
    new_password = body.password if body.mode is not AccessMode.OPEN else None
    await ctx.config.set_access(body.mode, new_password)

    # Keep this browser in: let in without a password until now, it gets a session.
    if session is OPEN_SESSION and body.mode is not AccessMode.OPEN:
        session = await start_session(request, response, body.remember)
    if new_password is not None:
        # A new password signs every other device out.
        others = {s.id for s in await ctx.sessions.list() if s.id != session.id}
        for session_id in others:
            await ctx.sessions.revoke(session_id)
        await ctx.hub.close_sessions(others)
    if body.mode is not AccessMode.OPEN:
        # Browsers let in without a password check again (LAN ones get back in).
        await ctx.hub.close_sessions({OPEN_SESSION.id})
    return {"ok": True}


def _valid_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(HOST_RE.match(host))


@router.put("/playback")
async def update_playback(
    body: PlaybackBody, request: Request, _session: Annotated[Session, Depends(require_session)]
) -> dict:
    ctx = get_ctx(request)
    if body.stream_format not in STREAM_FORMATS:
        raise _bad("invalid_stream_format")
    if body.max_bitrate not in BITRATES:
        raise _bad("invalid_bitrate")
    hosts = list(dict.fromkeys(h.strip() for h in body.known_hosts if h.strip()))
    bad = [h for h in hosts if not _valid_host(h)]
    if bad:
        raise _bad("invalid_host", host=bad[0])
    await ctx.config.save_playback(
        PlaybackConfig(
            stream_format=body.stream_format,
            max_bitrate=body.max_bitrate,
            preload_next=body.preload_next,
            known_hosts=tuple(hosts),
            scrobble=body.scrobble,
        )
    )
    ctx.apply_playback()
    return {"ok": True}
