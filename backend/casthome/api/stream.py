"""Audio stream proxy for the in-browser player.

The browser never talks to Navidrome directly (that would expose the
Navidrome credentials): it requests /api/stream/<id> with its session cookie
and CastHome relays Navidrome's response, including Range requests so the
<audio> element can seek.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from casthome.api.deps import get_ctx, require_session

router = APIRouter(prefix="/api", tags=["stream"], dependencies=[Depends(require_session)])

FORWARDED_HEADERS = ("content-type", "content-length", "content-range", "accept-ranges", "last-modified", "etag")
ALLOWED_FORMATS = {"mp3", "opus", "aac", "ogg", "flac", "raw"}


@router.get("/stream/{song_id}")
async def stream(
    song_id: str,
    request: Request,
    format: str | None = Query(None),  # noqa: A002 - mirrors the Subsonic parameter
    max_bitrate: int = Query(0, ge=0, le=1411),
) -> StreamingResponse:
    if format is not None and format not in ALLOWED_FORMATS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "unsupported_format"})
    upstream = await get_ctx(request).subsonic.open_stream(
        song_id, None if format == "raw" else format, max_bitrate, request.headers.get("range")
    )
    content_type = upstream.headers.get("content-type", "")
    if upstream.status_code >= 400 or content_type.startswith(("application/json", "text/xml", "application/xml")):
        # Subsonic reports errors (e.g. unknown id) as a JSON/XML body.
        await upstream.aclose()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "track_unplayable"})
    headers = {k: v for k in FORWARDED_HEADERS if (v := upstream.headers.get(k))}
    headers["Cache-Control"] = "private, no-transform"
    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=headers,
        background=BackgroundTask(upstream.aclose),
    )
