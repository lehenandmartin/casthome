"""WebSocket hub: pushes state to every connected browser.

Messages are `{"type": str, "data": object}`. Types:
- hello          full snapshot on connect: {player, queue, devices}
- player         playback state; `position` is the position at send time, which
                 clients interpolate from their own receive time while playing
- queue          full queue: {version, index, items}
- devices        list of discovered Cast devices
- notification   {level, code, params}; `code` is translated by the frontend
- auth_expired   the session is no longer valid; go back to the login page
- browser_cmd    only to the tab used as "This browser": load/play/pause/...

Client -> server (JSON): browser_status / browser_volume from that tab; the
plain text "ping" keeps the connection alive.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket

from casthome.background import spawn

log = logging.getLogger(__name__)


class Hub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._sessions: dict[WebSocket, str] = {}
        self._client_ids: dict[WebSocket, str] = {}
        self.client_names: dict[str, str] = {}
        self.on_client_gone: Callable[[str], None] | None = None
        self._pending: dict[str, Callable[[], Any]] = {}
        self._flush_scheduled = False

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def add(self, ws: WebSocket, session_id: str, client_id: str | None = None, name: str = "") -> None:
        self._clients.add(ws)
        self._sessions[ws] = session_id
        if client_id:
            # A reconnecting tab replaces its previous socket.
            for other, cid in list(self._client_ids.items()):
                if cid == client_id and other is not ws:
                    self._client_ids.pop(other, None)
            self._client_ids[ws] = client_id
            self.client_names[client_id] = name

    def remove(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        self._sessions.pop(ws, None)
        client_id = self._client_ids.pop(ws, None)
        if client_id and client_id not in self._client_ids.values() and self.on_client_gone:
            self.on_client_gone(client_id)

    def has_client(self, client_id: str) -> bool:
        return client_id in self._client_ids.values()

    async def send_to_client(self, client_id: str, msg_type: str, data: Any) -> None:
        """Send to one tab. Raises LookupError if that tab is not connected."""
        for ws, cid in list(self._client_ids.items()):
            if cid == client_id:
                await ws.send_text(json.dumps({"type": msg_type, "data": data}))
                return
        raise LookupError(client_id)

    async def close_sessions(self, session_ids: set[str], code: int = 4401) -> None:
        """Disconnect the browsers of revoked sessions (they then show the sign-in page)."""
        for ws, session_id in list(self._sessions.items()):
            if session_id in session_ids:
                self.remove(ws)
                try:
                    await ws.close(code=code)
                except Exception:  # noqa: BLE001 - already closed
                    pass

    def publish(self, msg_type: str, build: Callable[[], Any]) -> None:
        """Coalesce bursts: the latest builder per type is sent once per loop turn."""
        self._pending[msg_type] = build
        if not self._flush_scheduled:
            self._flush_scheduled = True
            asyncio.get_running_loop().call_soon(lambda: spawn(self._flush(), name='ws flush'))

    def send_now(self, msg_type: str, data: Any) -> None:
        """For events that must not be coalesced (notifications)."""
        spawn(self._broadcast(json.dumps({"type": msg_type, "data": data})), name='ws send')

    async def send(self, msg_type: str, data: Any) -> None:
        """Send now and wait for it (e.g. right before closing every socket)."""
        await self._broadcast(json.dumps({"type": msg_type, "data": data}))

    async def _flush(self) -> None:
        pending, self._pending = self._pending, {}
        self._flush_scheduled = False
        for msg_type, build in pending.items():
            await self._broadcast(json.dumps({"type": msg_type, "data": build()}))

    async def _broadcast(self, text: str) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text(text)
            except Exception:  # noqa: BLE001 - a closed socket is simply dropped
                dead.append(ws)
        for ws in dead:
            self.remove(ws)

    async def close_all(self, code: int = 4401) -> None:
        for ws in list(self._clients):
            try:
                await ws.close(code=code)
            except Exception:  # noqa: BLE001
                pass
        self._clients.clear()
        self._sessions.clear()
        self._client_ids.clear()
