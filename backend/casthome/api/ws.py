"""WebSocket endpoint (push only; commands go through REST)."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from casthome.api.deps import websocket_session
from casthome.background import spawn
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
    client_id = (ws.query_params.get("client") or "")[:64] or None
    client_name = (ws.query_params.get("name") or "")[:80]
    ctx.hub.add(ws, session.id, client_id, client_name)
    # A client opening the app is a good moment to pick up a queue saved elsewhere.
    spawn(ctx.coordinator.refresh_from_navidrome(), name='refresh queue')
    try:
        while True:
            message = await ws.receive_text()
            if message == "ping":
                await ws.send_text(json.dumps({"type": "pong", "data": None}))
                continue
            try:
                msg = json.loads(message)
            except ValueError:
                continue
            if client_id and isinstance(msg, dict) and isinstance(msg.get("data"), dict):
                ctx.browser_report(client_id, str(msg.get("type")), msg["data"])
    except WebSocketDisconnect:
        pass
    finally:
        ctx.hub.remove(ws)
