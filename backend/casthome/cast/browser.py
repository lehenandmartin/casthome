"""A browser tab used as a playback device ("This browser").

The playback coordinator drives it exactly like a Cast device: commands go to
the tab over its WebSocket (`browser_cmd`), and the tab's <audio> element
reports its state back (`browser_status`, `browser_volume`), which is turned
into the same events a Chromecast produces. The queue and the auto-advance
logic therefore stay on the server.
"""

from __future__ import annotations

from typing import Any, Protocol

from casthome.cast.types import (
    DEFAULT_MEDIA_RECEIVER_APP_ID,
    DeviceInfo,
    EventSink,
    MediaEvent,
    ReceiverEvent,
)

BROWSER_PREFIX = "browser:"
BROWSER_CAST_TYPE = "browser"


class ClientChannel(Protocol):
    async def send_to_client(self, client_id: str, msg_type: str, data: Any) -> None: ...


def browser_uuid(client_id: str) -> str:
    return f"{BROWSER_PREFIX}{client_id}"


def client_id_of(uuid: str) -> str | None:
    return uuid[len(BROWSER_PREFIX) :] if uuid.startswith(BROWSER_PREFIX) else None


class BrowserTarget:
    supports_preload = False  # the tab loads each track itself

    def __init__(self, client_id: str, name: str, channel: ClientChannel, sink: EventSink) -> None:
        self.client_id = client_id
        self.info = DeviceInfo(
            uuid=browser_uuid(client_id), name=name, model="", cast_type=BROWSER_CAST_TYPE, host="", port=0
        )
        self.sink = sink
        self._channel = channel

    async def _cmd(self, action: str, **data: Any) -> None:
        await self._channel.send_to_client(self.client_id, "browser_cmd", {"action": action, **data})

    async def load(self, url: str, content_type: str, metadata: dict[str, Any], start_at: float) -> None:
        await self._cmd("load", url=url, content_type=content_type, metadata=metadata, start_at=start_at)

    async def enqueue(self, url: str, content_type: str, metadata: dict[str, Any]) -> None:
        raise NotImplementedError("browsers do not preload")

    async def play(self) -> None:
        await self._cmd("play")

    async def pause(self) -> None:
        await self._cmd("pause")

    async def stop(self) -> None:
        await self._cmd("stop")

    async def seek(self, position: float) -> None:
        await self._cmd("seek", position=position)

    async def set_volume(self, level: float) -> None:
        await self._cmd("volume", level=max(0.0, min(1.0, level)))

    async def set_muted(self, muted: bool) -> None:
        await self._cmd("mute", muted=muted)

    async def request_status(self) -> None:
        await self._cmd("status")

    async def disconnect(self) -> None:
        try:
            await self._cmd("stop")
        except LookupError:
            pass  # the tab is already gone

    # --- reports from the tab -------------------------------------------------

    def report_status(self, data: dict[str, Any]) -> None:
        self.sink(
            MediaEvent(
                player_state=str(data.get("player_state", "UNKNOWN")),
                idle_reason=data.get("idle_reason"),
                content_id=data.get("content_id"),
                current_time=float(data.get("current_time") or 0.0),
                duration=float(data["duration"]) if data.get("duration") else None,
            )
        )

    def report_volume(self, data: dict[str, Any]) -> None:
        # Reported with the Default Media Receiver id so it never looks like a takeover.
        self.sink(
            ReceiverEvent(
                app_id=DEFAULT_MEDIA_RECEIVER_APP_ID,
                volume_level=float(data.get("volume") or 0.0),
                volume_muted=bool(data.get("muted")),
            )
        )
