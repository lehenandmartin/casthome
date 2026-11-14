"""Shared FastAPI dependencies: app context, session cookie, origin check."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request, Response, WebSocket, status

from casthome.auth.sessions import Session
from casthome.context import AppContext

COOKIE_NAME = "casthome_session"

# Who gets in without signing in (open access, or local network in LAN mode).
OPEN_SESSION = Session(
    id="open", persistent=False, created_at=0.0, last_seen_at=0.0, expires_at=0.0, user_agent="", ip=""
)


def client_host(conn: Request | WebSocket) -> str | None:
    return conn.client.host if conn.client else None


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


async def start_session(request: Request, response: Response, remember: bool) -> Session:
    """Sign this browser in: a new session and its cookie."""
    ctx = get_ctx(request)
    token, session = await ctx.sessions.create(
        persistent=remember, user_agent=request.headers.get("user-agent", ""), ip=client_host(request) or ""
    )
    set_session_cookie(response, ctx, token, remember, is_secure(request, ctx))
    return session


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
    if ctx.config.access_mode is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "setup_required"})
    token = request.cookies.get(COOKIE_NAME)
    result = await ctx.sessions.touch(token) if token else None
    if result is None:
        if ctx.config.open_for(client_host(request)):
            return OPEN_SESSION
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "not_signed_in"})
    if result.renewed and result.session.persistent:
        # Sliding expiry: push the cookie's Max-Age forward too.
        set_session_cookie(response, ctx, token, True, is_secure(request, ctx))  # type: ignore[arg-type]
    return result.session


async def websocket_session(ws: WebSocket) -> Session | None:
    ctx: AppContext = ws.app.state.ctx
    if not origin_allowed(ws.headers.get("origin"), ws.headers.get("host"), ws.headers.get("x-forwarded-host")):
        return None
    if ctx.config.access_mode is None:
        return None
    token = ws.cookies.get(COOKIE_NAME)
    result = await ctx.sessions.touch(token) if token else None
    if result is not None:
        return result.session
    return OPEN_SESSION if ctx.config.open_for(client_host(ws)) else None
