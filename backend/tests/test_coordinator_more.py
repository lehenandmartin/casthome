"""Playback coordinator: lifecycle, devices, seeking, volume, the status poll,
and failures (Navidrome or the device not answering). Fake device, no network."""

from __future__ import annotations

import asyncio

import pytest

from casthome.cast.types import ConnectionEvent, EventSink
from casthome.playback import coordinator as coordinator_module
from casthome.playback.coordinator import PlaybackCoordinator
from casthome.playback.media import MediaBuilder, StreamConfig
from casthome.playback.persistence import LoadedQueue
from casthome.playback.state import Notifier, PlaybackError, Status
from casthome.queue.logic import AddMode, QueueModel
from casthome.subsonic.client import NavidromeUnavailableError, NotAuthenticatedError
from casthome.subsonic.models import Song
from tests.test_coordinator import FakeStore, FakeTarget, Harness, songs


def loaded(n: int = 3, position: float = 0.0, device: str | None = "dev1", changed: str | None = "t1") -> LoadedQueue:
    model: QueueModel[Song] = QueueModel()
    model.play_context(songs(n), 0, None)
    return LoadedQueue(model=model, position=position, device_uuid=device, changed=changed)


class FlakyStore(FakeStore):
    """A store whose Navidrome is down, or which has a queue saved elsewhere."""

    def __init__(self, down: bool = False, elsewhere: LoadedQueue | None = None) -> None:
        super().__init__()
        self.down = down
        self.elsewhere = elsewhere

    async def load(self) -> LoadedQueue:
        if self.down:
            raise NavidromeUnavailableError("down")
        return await super().load()

    async def save(self, model, position, device_uuid):  # type: ignore[no-untyped-def]
        if self.down:
            raise NavidromeUnavailableError("down")
        await super().save(model, position, device_uuid)

    async def fetch_if_changed_elsewhere(self, last_changed: str | None) -> LoadedQueue | None:
        return self.elsewhere


@pytest.fixture
async def h():
    harness = Harness()
    await harness.c.start()
    await harness.c.select_device("dev1")
    yield harness
    for task in harness.c._tasks:
        task.cancel()


async def failing(*_args: object) -> None:
    raise OSError("device gone")


# --- lifecycle ------------------------------------------------------------------


async def test_stop_saves_the_queue_and_leaves_the_device(h):
    await h.c.play_songs(songs(), 0)
    await h.c.stop()
    assert h.store.saves[-1][0] == ["s0", "s1", "s2"]
    assert "disconnect" in h.target.calls


async def test_restore_without_navidrome_warns_and_keeps_an_empty_queue():
    h = Harness(FlakyStore(down=True))
    await h.c.restore()
    assert "navidrome_unavailable" in h.notifications
    assert len(h.c.queue) == 0


async def test_restore_forgets_a_browser_tab_but_keeps_a_cast_device():
    h = Harness(FakeStore(loaded(device="browser:abc", position=42.0)))
    await h.c.restore()
    assert h.c.device_uuid is None and h.c.position == 42.0 and h.c.duration == 200
    h = Harness(FakeStore(loaded(device="dev9")))
    await h.c.restore()
    assert h.c.device_uuid == "dev9"


async def test_queue_saved_by_another_client_is_picked_up_only_when_stopped(h):
    store = FlakyStore(elsewhere=loaded(n=2, position=12.0))
    h.c._store = store
    await h.c.play_songs(songs(5), 0)
    await h.c.refresh_from_navidrome()
    assert len(h.c.queue) == 5  # playing: left alone
    await h.c.stop_playback()
    await h.c.refresh_from_navidrome()
    assert len(h.c.queue) == 2 and h.c.position == 12.0


# --- devices --------------------------------------------------------------------


async def test_selected_device_is_connected_once_discovered():
    h = Harness(FakeStore(loaded(device="dev9")))
    await h.c.restore()
    h.c.on_devices_changed({"other"})
    await h.settle()
    assert h.targets == []
    h.c.on_devices_changed({"dev9"})
    await h.settle()
    assert h.c.target is not None and h.target.info.uuid == "dev9" and h.c.connected


async def test_unreachable_device_is_reported():
    notes: list[str] = []

    async def connector(uuid: str, sink: EventSink) -> FakeTarget:
        raise OSError("no route to host")

    media = MediaBuilder(StreamConfig(public_base_url="http://10.0.0.1:4533", username="me"), _pw)
    c = PlaybackCoordinator(connector, media, FakeStore(), Notifier(notify=lambda lvl, code, p: notes.append(code)))
    with pytest.raises(PlaybackError) as err:
        await c.select_device("dev1")
    assert err.value.code == "device_unreachable" and c.target is None and not c.connected
    c.device_uuid = "dev1"
    await c._connect_selected()  # found again by discovery: reported, not raised
    assert notes == ["device_unreachable"]


async def _pw() -> str:
    return "pw"


async def test_selecting_the_same_device_again_does_nothing(h):
    first = h.target
    await h.c.select_device("dev1")
    assert h.target is first and len(h.targets) == 1


async def test_switching_away_from_a_device_that_is_gone_still_works(h):
    await h.c.play_songs(songs(), 0)
    h.target.media("PLAYING", t=30.0)
    await h.settle()
    h.target.quit = failing  # type: ignore[method-assign]
    await h.c.select_device("dev2")
    assert h.target.info.uuid == "dev2" and h.target.loads[-1][1] == pytest.approx(30.0, abs=0.5)


async def test_device_back_online_is_asked_for_its_status(h):
    asked: list[bool] = []

    async def request_status() -> None:
        asked.append(True)

    h.target.request_status = request_status  # type: ignore[method-assign]
    h.target.sink(ConnectionEvent(False))
    await h.settle()
    assert not h.c.connected and "device_disconnected" in h.notifications
    h.target.sink(ConnectionEvent(True))
    await h.settle()
    assert h.c.connected and asked == [True]


# --- commands -------------------------------------------------------------------


async def test_seek_is_kept_within_the_track(h):
    await h.c.play_songs(songs(), 0)
    h.target.media("PLAYING", t=5.0)
    await h.settle()
    await h.c.seek(500)
    await h.c.seek(-3)
    assert h.target.calls[-2:] == [("seek", 200.0), ("seek", 0.0)]


async def test_seek_in_a_transcoded_track_reloads_it_at_the_offset(h):
    await h.c.play_songs(songs(suffix="dsf"), 0)
    assert "format=" in h.target.last_url
    h.target.media("PLAYING", t=5.0)
    await h.settle()
    await h.c.seek(60)
    assert h.target.loads[-1][1] == 60 and not any(c[0] == "seek" for c in h.target.calls if isinstance(c, tuple))


async def test_seek_when_stopped_only_moves_the_start(h):
    await h.c.add_songs(songs(), AddMode.QUEUE)
    await h.c.seek(30)
    assert h.c.position == 30 and h.target.loads == []
    await h.c.play()
    assert h.target.loads[-1][1] == 30


async def test_volume_and_mute_go_to_the_device(h):
    await h.c.set_volume(0.4)
    await h.c.set_muted(True)
    assert h.target.calls[-2:] == [("volume", 0.4), ("muted", True)]


async def test_a_device_that_does_not_answer_a_command_is_reported(h):
    h.target.set_volume = failing  # type: ignore[method-assign]
    with pytest.raises(PlaybackError) as err:
        await h.c.set_volume(0.4)
    assert err.value.code == "device_unreachable"


async def test_jump_to_a_queue_position(h):
    await h.c.play_songs(songs(), 0)
    await h.c.jump(2)
    assert "id=s2" in h.target.last_url
    with pytest.raises(PlaybackError) as err:
        await h.c.jump(7)
    assert err.value.code == "invalid_queue_index"


async def test_adding_to_an_empty_queue_cues_without_playing(h):
    await h.c.add_songs(songs(2), AddMode.QUEUE)
    assert h.c.queue.current.item.id == "s0" and h.c.status == Status.STOPPED and h.target.loads == []
    await h.c.add_songs(songs(1, suffix="mp3"), AddMode.NOW)
    assert len(h.target.loads) == 1


async def test_a_signed_out_session_cannot_play():
    async def no_password() -> str:
        raise NotAuthenticatedError("signed out")

    h = Harness()
    h.c._media = MediaBuilder(StreamConfig(public_base_url="http://10.0.0.1:4533", username="me"), no_password)
    await h.c.select_device("dev1")
    with pytest.raises(PlaybackError) as err:
        await h.c.play_songs(songs(), 0)
    assert err.value.code == "not_signed_in"


async def test_star_changes_reach_the_queue_copies(h):
    await h.c.play_songs([*songs(2), songs(1)[0]], 0)
    version = h.c.queue_version
    h.c.update_song_flags("s0", starred=True)
    assert [e.item.starred for e in h.c.queue.entries] == [True, False, True]
    assert h.c.queue_version == version + 1
    h.c.update_song_flags("unknown", starred=True)
    assert h.c.queue_version == version + 1


# --- failures and background work ------------------------------------------------


async def test_saving_without_navidrome_does_not_break_playback(h):
    h.c._store = FlakyStore(down=True)
    await h.c.play_songs(songs(), 0)
    await h.c.flush()
    assert h.c.status == Status.LOADING


async def test_an_event_that_fails_does_not_stop_the_next_ones(h):
    await h.c.play_songs(songs(), 0)
    h.target.request_status = failing  # type: ignore[method-assign]
    h.target.sink(ConnectionEvent(False))
    h.target.sink(ConnectionEvent(True))  # request_status fails here
    h.target.media("PLAYING", t=3.0)
    await h.settle()
    assert h.c.status == Status.PLAYING


async def test_status_poll_asks_the_device_and_saves_the_position(h, monkeypatch):
    monkeypatch.setattr(coordinator_module, "STATUS_POLL_INTERVAL_S", 0.001)
    monkeypatch.setattr(coordinator_module, "POSITION_SAVE_INTERVAL_S", 0)
    asked: list[bool] = []

    async def request_status() -> None:
        asked.append(True)

    await h.c.play_songs(songs(), 0)
    h.target.request_status = request_status  # type: ignore[method-assign]
    h.target.media("PLAYING", t=8.0)
    for task in h.c._tasks:
        task.cancel()
    await h.c.start()  # restart the poll with the short interval
    await asyncio.sleep(0.05)
    assert asked and h.store.saves and h.store.saves[-1][2] >= 8.0


async def test_status_poll_picks_up_a_queue_saved_elsewhere_when_idle(h, monkeypatch):
    monkeypatch.setattr(coordinator_module, "STATUS_POLL_INTERVAL_S", 0.001)
    monkeypatch.setattr(coordinator_module, "REMOTE_REFRESH_INTERVAL_S", 0)
    h.c._store = FlakyStore(elsewhere=loaded(n=4))
    for task in h.c._tasks:
        task.cancel()
    await h.c.start()
    await asyncio.sleep(0.05)
    assert len(h.c.queue) == 4
