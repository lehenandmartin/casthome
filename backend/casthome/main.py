"""FastAPI application factory and entry point."""

from __future__ import annotations

import logging
import mimetypes
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from casthome.api import auth, library, player, playlists, stream, ws
from casthome.api.deps import origin_allowed
from casthome.config import Settings, get_settings
from casthome.context import AppContext
from casthome.playback.coordinator import PlaybackError
from casthome.subsonic.client import NavidromeUnavailableError, NotAuthenticatedError, SubsonicError

log = logging.getLogger("casthome")

mimetypes.add_type("application/manifest+json", ".webmanifest")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def create_app(settings: Settings | None = None, ctx: AppContext | None = None, start_services: bool = True) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    context = ctx or AppContext.build(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await context.db.open()
        await context.sessions.purge_expired()
        if start_services:
            await context.coordinator.start()
            await context.coordinator.restore()
            await context.cast.start()
        yield
        if start_services:
            await context.coordinator.stop()
            await context.cast.stop()
        await context.subsonic.aclose()
        await context.db.close()

    app = FastAPI(title="CastHome", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.ctx = context

    @app.middleware("http")
    async def check_origin(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method not in SAFE_METHODS and not origin_allowed(
            request.headers.get("origin"), request.headers.get("host"), request.headers.get("x-forwarded-host")
        ):
            return JSONResponse({"code": "forbidden_origin"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "params": {"message": exc.detail}}
        return JSONResponse(detail, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(PlaybackError)
    async def playback_error(_request: Request, exc: PlaybackError) -> JSONResponse:
        return JSONResponse({"code": exc.code, "params": exc.params}, status_code=409)

    @app.exception_handler(NotAuthenticatedError)
    async def not_authenticated(_request: Request, _exc: NotAuthenticatedError) -> JSONResponse:
        return JSONResponse({"code": "not_signed_in"}, status_code=401)

    @app.exception_handler(NavidromeUnavailableError)
    async def navidrome_down(_request: Request, exc: NavidromeUnavailableError) -> JSONResponse:
        log.warning("Navidrome unavailable: %s", exc)
        return JSONResponse({"code": "navidrome_unavailable"}, status_code=503)

    @app.exception_handler(SubsonicError)
    async def subsonic_error(_request: Request, exc: SubsonicError) -> JSONResponse:
        return JSONResponse({"code": "navidrome_error", "params": {"message": exc.message}}, status_code=502)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "devices": len(context.cast.devices), "clients": context.hub.client_count}

    for module in (auth, player, library, playlists, stream, ws):
        app.include_router(module.router)

    dist = settings.frontend_dist
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> FileResponse:
            candidate = (dist / path).resolve()
            if path and candidate.is_file() and dist.resolve() in candidate.parents:
                # The service worker must be revalidated, or updates never reach clients.
                headers = {"Cache-Control": "no-cache"} if path == "sw.js" else None
                return FileResponse(candidate, headers=headers)
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
    else:
        log.warning("Frontend build not found at %s; serving the API only", dist)

    return app


def run() -> None:
    import sys

    import uvicorn
    from pydantic import ValidationError

    try:
        settings = get_settings()
    except ValidationError as exc:
        print("CastHome cannot start: invalid or missing configuration.", file=sys.stderr)
        for error in exc.errors():
            name = str(error["loc"][0]).upper() if error["loc"] else "?"
            print(f"  {name}: {error['msg']}", file=sys.stderr)
        print("Copy .env.example to .env at the repository root and fill it in.", file=sys.stderr)
        raise SystemExit(2) from None
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, proxy_headers=True)


if __name__ == "__main__":
    run()
