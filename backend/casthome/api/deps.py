"""Shared FastAPI dependencies: app context, session cookie, origin check."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request, Response, WebSocket, status

from casthome.auth.sessions import Session
from casthome.context import AppContext

COOKIE_NAME = "casthome_session"


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx  # type: ignore[no-any-return]


def set_session_cookie(response: Response, ctx: AppContext, token: str, persistent: bool, secure: bool) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        # No Max-Age: a browser-session cookie, dropped when the browser closes.
        max_age=int(ctx.sessions.lifetime(True)) if persistent else None,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def is_secure(request: Request, ctx: AppContext) -> bool:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return ctx.settings.cookie_secure or proto == "https"


def origin_allowed(origin: str | None, host: str | None, forwarded_host: str | None) -> bool:
    """Reject cross-site requests (CSRF / cross-site WebSocket hijacking)."""
    if not origin:
        return True  # non-browser clients and same-origin GETs may omit it
    origin_host = urlparse(origin).netloc
    return origin_host in {h for h in (host, forwarded_host) if h}


async def require_session(request: Request, response: Response) -> Session:
    ctx = get_ctx(request)
    token = request.cookies.get(COOKIE_NAME)
    result = await ctx.sessions.touch(token) if token else None
    if result is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "not_signed_in"})
    if result.renewed and result.session.persistent:
        # Sliding expiry: push the cookie's Max-Age forward too.
        set_session_cookie(response, ctx, token, True, is_secure(request, ctx))  # type: ignore[arg-type]
    return result.session


async def websocket_session(ws: WebSocket) -> Session | None:
    ctx: AppContext = ws.app.state.ctx
    if not origin_allowed(ws.headers.get("origin"), ws.headers.get("host"), ws.headers.get("x-forwarded-host")):
        return None
    token = ws.cookies.get(COOKIE_NAME)
    result = await ctx.sessions.touch(token) if token else None
    return result.session if result else None
