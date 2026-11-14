"""Sign-in to CastHome (its own password, not Navidrome's) and sessions."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from casthome.api.deps import COOKIE_NAME, OPEN_SESSION, access_host, client_host, get_ctx, require_session, start_session
from casthome.auth.sessions import Session

router = APIRouter(prefix="/api", tags=["auth"])

LOGIN_WINDOW_S = 300
LOGIN_MAX_ATTEMPTS = 10
_attempts: dict[str, deque[float]] = defaultdict(deque)


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
    remember: bool = False


def throttle(ip: str) -> None:
    """Limit password guesses per client address."""
    now = time.monotonic()
    window = _attempts[ip]
    while window and now - window[0] > LOGIN_WINDOW_S:
        window.popleft()
    if len(window) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "too_many_attempts"})
    window.append(now)


def throttle_passed(ip: str) -> None:
    _attempts.pop(ip, None)


@router.get("/status")
async def app_status(request: Request) -> dict:
    """Public: what the browser should show first (setup, sign-in or the app)."""
    ctx = get_ctx(request)
    needs = await ctx.setup_needs()
    signed_in = False
    if not needs["access"]:
        token = request.cookies.get(COOKIE_NAME)
        signed_in = ctx.config.open_for(access_host(request)) or (
            token is not None and await ctx.sessions.touch(token) is not None
        )
    return {
        "setup_required": any(needs.values()),
        "setup": needs,
        "signed_in": signed_in,
    }


@router.post("/auth/login")
async def login(body: LoginBody, request: Request, response: Response) -> dict:
    ctx = get_ctx(request)
    if ctx.config.access_mode is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "setup_required"})
    ip = client_host(request) or ""
    throttle(ip)
    if not await ctx.config.check_password(body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "invalid_credentials"})
    throttle_passed(ip)
    await start_session(request, response, body.remember)
    return {"ok": True}


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request, response: Response, session: Annotated[Session, Depends(require_session)]
) -> None:
    ctx = get_ctx(request)
    if session is not OPEN_SESSION:
        await ctx.sessions.revoke(session.id)
        await ctx.hub.close_sessions({session.id})
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/auth/me")
async def me(request: Request, session: Annotated[Session, Depends(require_session)]) -> dict:
    ctx = get_ctx(request)
    navidrome = ctx.config.navidrome
    return {
        "username": navidrome.username if navidrome else None,
        "session_id": session.id,
        "access_mode": ctx.config.access_mode,
        # Let in without a password: nothing to sign out of.
        "open_session": session is OPEN_SESSION,
    }


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
