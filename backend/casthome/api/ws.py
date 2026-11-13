"""WebSocket endpoint (push only; commands go through REST)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from casthome.api.deps import websocket_session
from casthome.context import AppContext

router = APIRouter()

WS_UNAUTHORIZED = 4401


@router.websocket("/api/ws")
async def websocket(ws: WebSocket) -> None:
    ctx: AppContext = ws.app.state.ctx
    session = await websocket_session(ws)
    # Accept before closing: a close during the handshake reaches browsers as a
    # generic failure (1006), while 4401 tells the client to show the sign-in page.
    await ws.accept()
    if session is None:
        await ws.close(code=WS_UNAUTHORIZED)
        return
    await ws.send_text(json.dumps({"type": "hello", "data": ctx.full_snapshot()}))
    ctx.hub.add(ws, session.id)
    # A client opening the app is a good moment to pick up a queue saved elsewhere.
    asyncio.create_task(ctx.coordinator.refresh_from_navidrome())
    try:
        while True:
            message = await ws.receive_text()
            if message == "ping":
                await ws.send_text(json.dumps({"type": "pong", "data": None}))
    except WebSocketDisconnect:
        pass
    finally:
        ctx.hub.remove(ws)
