"""Sign-in, sign-out and session management."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from casthome.api.deps import COOKIE_NAME, get_ctx, is_secure, require_session, set_session_cookie
from casthome.auth.sessions import Session
from casthome.subsonic.client import InvalidCredentialsError

router = APIRouter(prefix="/api", tags=["auth"])

LOGIN_WINDOW_S = 300
LOGIN_MAX_ATTEMPTS = 10
_attempts: dict[str, deque[float]] = defaultdict(deque)


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
    remember: bool = False


def _throttle(ip: str) -> None:
    now = time.monotonic()
    window = _attempts[ip]
    while window and now - window[0] > LOGIN_WINDOW_S:
        window.popleft()
    if len(window) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "too_many_attempts"})
    window.append(now)


@router.post("/auth/login")
async def login(body: LoginBody, request: Request, response: Response) -> dict:
    ctx = get_ctx(request)
    ip = request.client.host if request.client else ""
    _throttle(ip)
    try:
        await ctx.subsonic.ping(password=body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "invalid_credentials"}) from exc
    _attempts.pop(ip, None)
    had_credentials = await ctx.credentials.get_password() is not None
    await ctx.credentials.set_password(body.password)
    token, _session = await ctx.sessions.create(
        persistent=body.remember, user_agent=request.headers.get("user-agent", ""), ip=ip
    )
    set_session_cookie(response, ctx, token, body.remember, is_secure(request, ctx))
    if not had_credentials:
        # First sign-in (or after a password change): load the Navidrome play queue now.
        asyncio.create_task(ctx.coordinator.restore())
    return {"username": ctx.settings.navidrome_username}


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request, response: Response, session: Annotated[Session, Depends(require_session)]
) -> None:
    ctx = get_ctx(request)
    await ctx.sessions.revoke(session.id)
    await ctx.hub.close_sessions({session.id})
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/auth/me")
async def me(request: Request, session: Annotated[Session, Depends(require_session)]) -> dict:
    return {"username": get_ctx(request).settings.navidrome_username, "session_id": session.id}


@router.get("/sessions")
async def list_sessions(request: Request, session: Annotated[Session, Depends(require_session)]) -> list[dict]:
    sessions = await get_ctx(request).sessions.list()
    return [{**s.__dict__, "current": s.id == session.id} for s in sessions]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str, request: Request, _session: Annotated[Session, Depends(require_session)]
) -> None:
    ctx = get_ctx(request)
    if not await ctx.sessions.revoke(session_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "session_not_found"})
    await ctx.hub.close_sessions({session_id})


@router.delete("/sessions", status_code=204)
async def revoke_other_sessions(request: Request, session: Annotated[Session, Depends(require_session)]) -> None:
    """Sign out every other device."""
    ctx = get_ctx(request)
    others = {s.id for s in await ctx.sessions.list() if s.id != session.id}
    for session_id in others:
        await ctx.sessions.revoke(session_id)
    await ctx.hub.close_sessions(others)
