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

from casthome import __version__
from casthome.api import auth, home, library, player, playlists, server, setup, stream, ws
from casthome.api.deps import origin_allowed
from casthome.config import Settings, get_settings
from casthome.context import AppContext
from casthome.playback.coordinator import PlaybackError
from casthome.subsonic.client import (
    InvalidCredentialsError,
    NavidromeUnavailableError,
    NotAuthenticatedError,
    SubsonicError,
)

log = logging.getLogger("casthome")

mimetypes.add_type("application/manifest+json", ".webmanifest")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def create_app(settings: Settings | None = None, ctx: AppContext | None = None, start_services: bool = True) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    context = ctx or AppContext.build(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await context.open()
        await context.sessions.purge_expired()
        needs = await context.setup_needs()
        if any(needs.values()):
            log.warning("CastHome is not set up yet: open it in a browser to finish the setup")
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

    app = FastAPI(title="CastHome", version=__version__, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
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
    async def not_configured(_request: Request, _exc: NotAuthenticatedError) -> JSONResponse:
        return JSONResponse({"code": "navidrome_not_configured"}, status_code=503)

    @app.exception_handler(InvalidCredentialsError)
    async def credentials_rejected(_request: Request, _exc: InvalidCredentialsError) -> JSONResponse:
        return JSONResponse({"code": "navidrome_credentials_rejected"}, status_code=502)

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

    for module in (setup, auth, server, home, player, library, playlists, stream, ws):
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


def _check_data_dir(settings: Settings) -> None:
    """Stop with a clear message when the data folder is not writable."""
    import os
    import sys

    data_dir = settings.data_dir
    probe = data_dir / ".write-test"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        print(f"CastHome cannot write to its data folder {data_dir}: {exc.strerror}.", file=sys.stderr)
        uid = os.getuid() if hasattr(os, "getuid") else "?"
        print(
            f"It runs as user {uid}. Give it the folder (on the host: chown -R {uid} <folder>),"
            " or with Docker set PUID/PGID to the folder's owner.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None


def run() -> None:
    import sys

    import uvicorn
    from pydantic import ValidationError

    try:
        settings = get_settings()
    except ValidationError as exc:
        print("CastHome cannot start: invalid environment variable.", file=sys.stderr)
        for error in exc.errors():
            name = str(error["loc"][0]).upper() if error["loc"] else "?"
            print(f"  {name}: {error['msg']}", file=sys.stderr)
        print("Fix or remove it (in .env or the environment); see .env.example.", file=sys.stderr)
        raise SystemExit(2) from None
    _check_data_dir(settings)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, proxy_headers=True)


if __name__ == "__main__":
    run()
