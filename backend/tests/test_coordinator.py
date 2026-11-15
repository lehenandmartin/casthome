"""Playback coordinator against a fake Cast device: no network involved."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from casthome.cast.types import (
    DEFAULT_MEDIA_RECEIVER_APP_ID,
    DeviceInfo,
    EventSink,
    LoadFailedEvent,
    MediaEvent,
    ReceiverEvent,
)
from casthome.playback.coordinator import Notifier, PlaybackCoordinator, PlaybackError, Status
from casthome.playback.media import MediaBuilder, StreamConfig
from casthome.playback.persistence import LoadedQueue
from casthome.queue.logic import AddMode, QueueModel, RepeatMode
from casthome.subsonic.models import Song


class FakeTarget:
    def __init__(self, uuid: str, sink: EventSink) -> None:
        self.info = DeviceInfo(uuid, "Living room", "Chromecast", "cast", "10.0.0.2", 8009)
        self.sink = sink
        self.loads: list[tuple[str, float]] = []
        self.enqueued: list[str] = []
        self.calls: list[Any] = []

    @property
    def last_url(self) -> str:
        return self.loads[-1][0]

    async def load(self, url: str, content_type: str, metadata: dict, start_at: float) -> None:
        self.loads.append((url, start_at))

    async def enqueue(self, url: str, content_type: str, metadata: dict) -> None:
        self.enqueued.append(url)

    async def play(self) -> None:
        self.calls.append("play")

    async def pause(self) -> None:
        self.calls.append("pause")

    async def stop(self) -> None:
        self.calls.append("stop")

    async def quit(self) -> None:
        self.calls.append("quit")

    async def seek(self, position: float) -> None:
        self.calls.append(("seek", position))

    async def set_volume(self, level: float) -> None:
        self.calls.append(("volume", level))

    async def set_muted(self, muted: bool) -> None:
        self.calls.append(("muted", muted))

    async def request_status(self) -> None:
        pass

    async def disconnect(self) -> None:
        self.calls.append("disconnect")

    # helpers emitting device events
    def media(self, state: str, reason: str | None = None, t: float = 0.0, url: str | None = None) -> None:
        self.sink(MediaEvent(state, reason, url or self.last_url, t, 200.0))


class FakeStore:
    def __init__(self, loaded: LoadedQueue | None = None) -> None:
        self.saves: list[tuple[list[str], int | None, float]] = []
        self.loaded = loaded

    async def load(self) -> LoadedQueue:
        assert self.loaded is not None
        return self.loaded

    async def save(self, model: QueueModel[Song], position: float, device_uuid: str | None) -> None:
        self.saves.append(([e.item.id for e in model.entries], model.index, position))

    async def fetch_if_changed_elsewhere(self, last_changed: str | None) -> LoadedQueue | None:
        return None


def songs(n: int = 3, suffix: str = "flac") -> list[Song]:
    return [Song(id=f"s{i}", title=f"Track {i}", suffix=suffix, duration=200) for i in range(n)]


async def _pw() -> str:
    return "pw"


class Harness:
    def __init__(self, store: FakeStore | None = None) -> None:
        self.targets: list[FakeTarget] = []
        self.notifications: list[str] = []
        self.store = store or FakeStore()

        async def connector(uuid: str, sink: EventSink) -> FakeTarget:
            target = FakeTarget(uuid, sink)
            self.targets.append(target)
            return target

        media = MediaBuilder(StreamConfig(public_base_url="http://10.0.0.1:4533", username="me"), _pw)
        self.c = PlaybackCoordinator(
            connector,
            media,
            self.store,
            Notifier(notify=lambda level, code, params: self.notifications.append(code)),
        )

    @property
    def target(self) -> FakeTarget:
        return self.targets[-1]

    async def settle(self) -> None:
        for _ in range(5):
            await asyncio.sleep(0)


@pytest.fixture
async def h():
    harness = Harness()
    await harness.c.start()
    await harness.c.select_device("dev1")
    yield harness
    for task in harness.c._tasks:
        task.cancel()


def playing_id(h: Harness) -> str:
    return h.c.queue.current.item.id


async def test_play_album_loads_first_track(h):
    await h.c.play_songs(songs(), 0)
    assert len(h.target.loads) == 1 and "id=s0" in h.target.last_url
    assert h.c.status == Status.LOADING
    h.target.media("PLAYING", t=1.0)
    await h.settle()
    assert h.c.status == Status.PLAYING


async def test_natural_end_loads_next_then_stops_at_end(h):
    await h.c.play_songs(songs(2), 0)
    h.target.media("PLAYING")
    h.target.media("IDLE", "FINISHED")
    await h.settle()
    assert playing_id(h) == "s1" and len(h.target.loads) == 2
    h.target.media("PLAYING")
    h.target.media("IDLE", "FINISHED")
    await h.settle()
    assert h.c.status == Status.STOPPED and len(h.target.loads) == 2
    assert "queue_ended" in h.notifications


async def test_duplicate_finished_is_ignored(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING")
    first_url = h.target.last_url
    h.target.media("IDLE", "FINISHED")
    h.target.media("IDLE", "FINISHED", url=first_url)
    await h.settle()
    assert playing_id(h) == "s1" and len(h.target.loads) == 2


async def test_finished_before_playing_is_ignored(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("IDLE", "FINISHED")  # stale status from before our load
    await h.settle()
    assert playing_id(h) == "s0" and len(h.target.loads) == 1


async def test_interrupted_from_our_own_load_is_ignored(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING")
    old = h.target.last_url
    await h.c.next()
    h.target.media("IDLE", "INTERRUPTED", url=old)
    await h.settle()
    assert h.c.status == Status.LOADING and playing_id(h) == "s1"


async def test_external_stop_does_not_advance(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING")
    h.target.media("IDLE", "CANCELLED")
    await h.settle()
    assert h.c.status == Status.STOPPED and playing_id(h) == "s0" and len(h.target.loads) == 1


async def test_repeat_one_replays(h):
    await h.c.play_songs(songs(3), 0)
    await h.c.set_mode(repeat=RepeatMode.ONE)
    h.target.media("PLAYING")
    h.target.media("IDLE", "FINISHED")
    await h.settle()
    assert playing_id(h) == "s0" and len(h.target.loads) == 2


async def test_error_retries_transcoded_then_skips(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("IDLE", "ERROR")
    await h.settle()
    assert playing_id(h) == "s0" and "format=mp3" in h.target.last_url
    h.target.sink(LoadFailedEvent(error_code=104))
    await h.settle()
    assert playing_id(h) == "s1" and "format=" not in h.target.last_url
    assert "track_unplayable" in h.notifications


async def test_too_many_errors_stops(h):
    await h.c.play_songs(songs(10), 0)
    for _ in range(10):
        h.target.media("IDLE", "ERROR")
        await h.settle()
    assert h.c.status == Status.STOPPED
    assert "too_many_errors" in h.notifications
    assert playing_id(h) == "s4"


async def test_previous_restarts_after_three_seconds(h):
    await h.c.play_songs(songs(3), 1)
    h.target.media("PLAYING", t=10.0)
    await h.settle()
    await h.c.previous()
    assert ("seek", 0.0) in h.target.calls and playing_id(h) == "s1"
    h.target.media("PLAYING", t=1.0)
    await h.settle()
    await h.c.previous()
    assert playing_id(h) == "s0" and len(h.target.loads) == 2


async def test_previous_on_first_track_restarts(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING", t=1.0)
    await h.settle()
    await h.c.previous()
    assert ("seek", 0.0) in h.target.calls and len(h.target.loads) == 1


async def test_pause_and_resume(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING", t=5.0)
    await h.settle()
    await h.c.toggle()
    assert h.target.calls[-1] == "pause"
    h.target.media("PAUSED", t=5.0)
    await h.settle()
    await h.c.toggle()
    assert h.target.calls[-1] == "play"


async def test_next_when_stopped_only_cues(h):
    h.c.queue.replace(songs(3), 0)
    await h.c.next()
    assert playing_id(h) == "s1" and h.target.loads == []


async def test_play_when_stopped_resumes_at_position(h):
    h.c.queue.replace(songs(3), 1)
    h.c.position = 42.0
    await h.c.play()
    assert h.target.loads[-1][1] == 42.0 and "id=s1" in h.target.last_url


async def test_add_next_does_not_interrupt(h):
    await h.c.play_songs(songs(2), 0)
    await h.c.add_songs([Song(id="x", title="X")], AddMode.QUEUE)
    assert [e.item.id for e in h.c.queue.entries] == ["s0", "x", "s1"]
    assert len(h.target.loads) == 1


async def test_other_app_takes_over(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING")
    h.target.sink(ReceiverEvent(app_id=DEFAULT_MEDIA_RECEIVER_APP_ID, volume_level=0.5, volume_muted=False))
    await h.settle()
    assert h.c.volume == 0.5
    h.target.sink(ReceiverEvent(app_id="SPOTIFY", volume_level=0.5, volume_muted=False))
    await h.settle()
    assert h.c.status == Status.STOPPED and "device_taken_over" in h.notifications


async def test_switching_device_transfers_playback(h):
    await h.c.play_songs(songs(3), 1)
    first = h.target
    h.target.media("PLAYING", t=30.0)
    await h.settle()
    await h.c.select_device("dev2")
    assert first.calls[-2:] == ["quit", "disconnect"]  # quit: the session is ended, not left open
    assert h.target is not first
    assert "id=s1" in h.target.last_url and h.target.loads[-1][1] >= 30.0


async def test_commands_without_device_fail_cleanly():
    harness = Harness()
    harness.c.queue.replace(songs(2), 0)
    with pytest.raises(PlaybackError) as err:
        await harness.c.play()
    assert err.value.code == "no_device"


async def test_restore_reattaches_to_media_still_playing():
    model: QueueModel[Song] = QueueModel()
    model.replace(songs(3), 2)
    harness = Harness(FakeStore(LoadedQueue(model=model, position=12.0, device_uuid="dev1", changed=None)))
    await harness.c.start()
    await harness.c.restore()
    assert harness.c.device_uuid == "dev1" and harness.c.status == Status.STOPPED
    await harness.c._connect_selected()
    url = "http://10.0.0.1:4533/rest/stream?id=s2&u=me&t=x&s=y&v=1.16.1&c=CastHome"
    harness.target.sink(MediaEvent("PLAYING", None, url, 50.0, 200.0))
    await harness.settle()
    assert harness.c.status == Status.PLAYING and harness.c.position == 50.0
    harness.target.sink(MediaEvent("IDLE", "FINISHED", url, 200.0, 200.0))
    await harness.settle()
    assert harness.c.status == Status.STOPPED  # s2 was the last track
    for task in harness.c._tasks:
        task.cancel()


async def test_restore_ignores_foreign_media():
    model: QueueModel[Song] = QueueModel()
    model.replace(songs(3), 0)
    harness = Harness(FakeStore(LoadedQueue(model=model, position=0, device_uuid="dev1", changed=None)))
    await harness.c.start()
    await harness.c.restore()
    await harness.c._connect_selected()
    harness.target.sink(MediaEvent("PLAYING", None, "https://youtube.example/v", 5.0, 100.0))
    await harness.settle()
    assert harness.c.status == Status.STOPPED
    for task in harness.c._tasks:
        task.cancel()


def uid_of(h: Harness, song_id: str) -> int:
    return next(e.uid for e in h.c.queue.entries if e.item.id == song_id)


async def test_remove_current_while_playing_loads_following(h):
    await h.c.play_songs(songs(3), 0)
    h.target.media("PLAYING")
    await h.settle()
    await h.c.remove_entry(uid_of(h, "s0"))
    assert playing_id(h) == "s1" and "id=s1" in h.target.last_url


async def test_remove_last_current_while_playing_stops(h):
    await h.c.play_songs(songs(2), 1)
    h.target.media("PLAYING")
    await h.settle()
    await h.c.remove_entry(uid_of(h, "s1"))
    assert h.c.status == Status.STOPPED and "stop" in h.target.calls


async def test_remove_other_entry_does_not_reload(h):
    await h.c.play_songs(songs(3), 0)
    await h.c.remove_entry(uid_of(h, "s2"))
    assert len(h.target.loads) == 1 and [e.item.id for e in h.c.queue.entries] == ["s0", "s1"]


async def test_move_keeps_playing_entry(h):
    await h.c.play_songs(songs(3), 0)
    version = h.c.queue_version
    await h.c.move_entry(uid_of(h, "s2"), 0)
    assert [e.item.id for e in h.c.queue.entries] == ["s2", "s0", "s1"]
    assert playing_id(h) == "s0" and len(h.target.loads) == 1 and h.c.queue_version > version


async def test_unknown_uid_is_reported(h):
    await h.c.play_songs(songs(2), 0)
    with pytest.raises(PlaybackError) as err:
        await h.c.remove_entry(9999)
    assert err.value.code == "invalid_queue_index"
    with pytest.raises(PlaybackError):
        await h.c.move_entry(uid_of(h, "s0"), 5)


async def test_jump_by_uid(h):
    await h.c.play_songs(songs(3), 0)
    await h.c.jump_uid(uid_of(h, "s2"))
    assert playing_id(h) == "s2" and "id=s2" in h.target.last_url


async def test_new_album_keeps_next_in_queue_and_names_context(h):
    await h.c.play_songs(songs(2), 0, "First album")
    await h.c.add_songs([Song(id="x", title="X")], AddMode.QUEUE)
    await h.c.play_songs([Song(id="k", title="K"), Song(id="l", title="L")], 0, "Second album")
    snap = h.c.queue_snapshot()
    assert [i["id"] for i in snap["items"]] == ["k", "x", "l"]
    assert [i["queued"] for i in snap["items"]] == [False, True, False]
    assert snap["context_name"] == "Second album"


async def test_finished_track_plays_queued_before_album(h):
    await h.c.play_songs(songs(3), 0)
    await h.c.add_songs([Song(id="x", title="X", duration=200)], AddMode.QUEUE)
    h.target.media("PLAYING")
    h.target.media("IDLE", "FINISHED")
    await h.settle()
    assert playing_id(h) == "x"
    h.target.media("PLAYING")
    h.target.media("IDLE", "FINISHED")
    await h.settle()
    assert playing_id(h) == "s1"


async def test_clear_queued_keeps_album(h):
    await h.c.play_songs(songs(3), 0)
    await h.c.add_songs([Song(id="x", title="X")], AddMode.QUEUE)
    await h.c.clear_queued()
    assert [e.item.id for e in h.c.queue.entries] == ["s0", "s1", "s2"] and len(h.target.loads) == 1


async def test_events_from_a_device_we_left_are_ignored(h):
    await h.c.play_songs(songs(2), 0)
    old = h.target
    await h.c.select_device("dev2")
    old.sink(ReceiverEvent(app_id=None, volume_level=0.9, volume_muted=True))  # its session closing
    await h.settle()
    assert h.c.volume != 0.9 and h.c.muted is False


# --- edge cases ----------------------------------------------------------------


async def test_empty_queue_commands_do_nothing(h):
    for command in (h.c.next, h.c.previous, h.c.toggle, h.c.play, h.c.pause):
        await command()
    assert h.target.loads == [] and h.c.queue.current is None and h.c.status == Status.STOPPED


async def test_clear_while_playing_stops_and_empties(h):
    await h.c.play_songs(songs(3), 1)
    h.target.media("PLAYING", t=5.0)
    await h.settle()
    await h.c.clear()
    assert len(h.c.queue) == 0 and h.c.queue.current is None and h.c.status == Status.STOPPED
    # Nothing to play afterwards, and no error.
    await h.c.next()
    await h.c.play()
    assert len(h.target.loads) == 1


async def test_two_quick_plays_end_with_the_last_one(h):
    first = [Song(id=f"a{i}", title=f"a{i}", duration=200) for i in range(3)]
    second = [Song(id=f"b{i}", title=f"b{i}", duration=200) for i in range(2)]
    await asyncio.gather(h.c.play_songs(first, 0, "A"), h.c.play_songs(second, 1, "B"))
    assert playing_id(h) == "b1" and h.c.queue.context_name == "B"
    assert [e.item.id for e in h.c.queue.entries] == ["b0", "b1"]
    assert "id=b1" in h.target.last_url


async def test_shuffled_album_starts_with_the_chosen_track(h):
    await h.c.set_mode(shuffle=True)
    await h.c.play_songs(songs(8), 3)
    assert playing_id(h) == "s3" and sorted(e.item.id for e in h.c.queue.entries) == sorted(s.id for s in songs(8))


async def test_moving_to_an_invalid_position_is_reported(h):
    await h.c.play_songs(songs(3), 0)
    uid = h.c.queue.entries[1].uid
    with pytest.raises(PlaybackError) as err:
        await h.c.move_entry(uid, 99)
    assert err.value.code == "invalid_queue_index"
    assert [e.item.id for e in h.c.queue.entries] == ["s0", "s1", "s2"]


# --- updates sent to browsers while playing ------------------------------------


async def test_polled_status_is_sent_only_when_browsers_could_not_guess_it(h):
    now = [1000.0]
    h.c._clock = lambda: now[0]
    sent: list[int] = []

    def changed() -> None:
        sent.append(1)
        h.c.player_snapshot(None)  # what the hub does: build and send the state

    h.c.notifier = Notifier(player_changed=changed)
    await h.c.play_songs(songs(3), 0)
    sent.clear()

    h.target.media("PLAYING", t=0.0)
    await h.settle()
    assert len(sent) == 1  # started playing

    for t in (2.0, 4.0, 6.0):  # regular polls, position where expected
        now[0] += 2.0
        h.target.media("PLAYING", t=t + 0.3)
        await h.settle()
    assert len(sent) == 1

    now[0] += 2.0
    h.target.media("PLAYING", t=60.0)  # jumped (seek on the device)
    await h.settle()
    assert len(sent) == 2

    now[0] += 2.0
    h.target.media("PAUSED", t=62.0)
    await h.settle()
    assert len(sent) == 3 and h.c.status == Status.PAUSED

    now[0] += 2.0
    h.target.media("PAUSED", t=62.0)  # still paused: nothing new
    await h.settle()
    assert len(sent) == 3
