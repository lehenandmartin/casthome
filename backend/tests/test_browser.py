"""The browser tab as a playback device, driven like a Cast device."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from casthome.cast.browser import BrowserTarget, browser_uuid, client_id_of
from casthome.cast.types import ConnectionEvent, EventSink
from casthome.playback.coordinator import PlaybackCoordinator, Status
from casthome.playback.media import MediaBuilder, StreamConfig
from casthome.ws.hub import Hub
from tests.test_coordinator import FakeStore, songs


class Channel:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, dict[str, Any]]] = []
        self.connected = {"tab1"}

    async def send_to_client(self, client_id: str, msg_type: str, data: Any) -> None:
        if client_id not in self.connected:
            raise LookupError(client_id)
        self.sent.append((client_id, msg_type, data))

    def last(self, action: str) -> dict[str, Any]:
        return next(d for _, _, d in reversed(self.sent) if d["action"] == action)


async def _pw() -> str:
    return "secret-password"


@pytest.fixture
async def setup():
    channel = Channel()
    targets: list[BrowserTarget] = []

    async def connector(uuid: str, sink: EventSink) -> BrowserTarget:
        client_id = client_id_of(uuid)
        assert client_id is not None
        target = BrowserTarget(client_id, "Safari on iPhone", channel, sink)
        targets.append(target)
        return target

    media = MediaBuilder(StreamConfig(public_base_url="http://10.0.0.1:4533", username="me"), _pw)
    c = PlaybackCoordinator(connector, media, FakeStore(), preload_next=True)
    await c.start()
    await c.select_device(browser_uuid("tab1"))
    yield c, channel, targets
    for task in c._tasks:
        task.cancel()


async def settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_browser_gets_proxied_urls_without_credentials(setup):
    c, channel, _ = setup
    await c.play_songs(songs(2), 0)
    load = channel.last("load")
    assert load["url"].startswith("/api/stream/s0?")
    assert "secret-password" not in str(load) and "t=" not in load["url"] and "u=" not in load["url"]


async def test_browser_reports_drive_auto_advance(setup):
    c, channel, targets = setup
    await c.play_songs(songs(2), 0)
    url = channel.last("load")["url"]
    targets[-1].report_status({"player_state": "PLAYING", "content_id": url, "current_time": 1, "duration": 200})
    await settle()
    assert c.status == Status.PLAYING
    # Near the end: browsers never preload.
    targets[-1].report_status({"player_state": "PLAYING", "content_id": url, "current_time": 190, "duration": 200})
    await settle()
    assert c._preload is None
    targets[-1].report_status({"player_state": "IDLE", "idle_reason": "FINISHED", "content_id": url})
    await settle()
    assert c.queue.current.item.id == "s1" and channel.last("load")["url"].startswith("/api/stream/s1?")


async def test_error_retries_transcoded_in_browser(setup):
    c, channel, targets = setup
    await c.play_songs(songs(2), 0)
    url = channel.last("load")["url"]
    targets[-1].report_status({"player_state": "IDLE", "idle_reason": "ERROR", "content_id": url})
    await settle()
    assert "format=mp3" in channel.last("load")["url"]


async def test_closing_the_tab_stops_and_forgets_the_device(setup):
    c, _, targets = setup
    await c.play_songs(songs(2), 0)
    targets[-1].sink(ConnectionEvent(connected=False))
    await settle()
    assert c.status == Status.STOPPED and c.target is None and c.device_uuid is None


async def test_volume_reports_do_not_look_like_a_takeover(setup):
    c, channel, targets = setup
    await c.play_songs(songs(2), 0)
    url = channel.last("load")["url"]
    targets[-1].report_status({"player_state": "PLAYING", "content_id": url, "current_time": 1, "duration": 200})
    targets[-1].report_volume({"volume": 0.3, "muted": False})
    await settle()
    assert c.status == Status.PLAYING and c.volume == 0.3


async def test_a_browsers_volume_is_left_to_its_device(setup):
    # The phone or computer sets it (buttons, system volume): CastHome never does.
    c, channel, _ = setup
    await c.play_songs(songs(2), 0)
    await c.set_volume(0.2)
    await c.set_muted(True)
    assert not [d for _, _, d in channel.sent if d["action"] in ("volume", "mute")]


async def test_switching_from_browser_to_cast_stops_the_tab(setup):
    c, channel, _ = setup
    await c.play_songs(songs(2), 0)
    channel.connected.add("tab2")
    await c.select_device(browser_uuid("tab2"))
    assert channel.sent[-2][0] == "tab1" and channel.sent[-2][2]["action"] == "stop"


def test_hub_reports_a_tab_gone_only_when_its_last_socket_closes():
    hub = Hub()
    gone: list[str] = []
    hub.on_client_gone = gone.append
    first, second = object(), object()
    hub.add(first, "sess", "tab1")  # type: ignore[arg-type]
    hub.add(second, "sess", "tab1")  # type: ignore[arg-type]  # reconnect replaces it
    hub.remove(first)  # type: ignore[arg-type]
    assert gone == [] and hub.has_client("tab1")
    hub.remove(second)  # type: ignore[arg-type]
    assert gone == ["tab1"] and not hub.has_client("tab1")
