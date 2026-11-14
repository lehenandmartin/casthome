import asyncio

from casthome.scrobble.scrobbler import Scrobbler, threshold
from tests.test_coordinator import Harness, songs


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make():
    calls: list[tuple[str, bool, int | None]] = []

    async def sink(song_id: str, submission: bool, time_ms: int | None) -> None:
        calls.append((song_id, submission, time_ms))

    clock = Clock()
    return Scrobbler(sink, clock), clock, calls


async def play(s: Scrobbler, clock: Clock, song_id: str, start: float, seconds: int, step: float = 2.0) -> None:
    pos = start
    await s.progress(song_id, pos)
    for _ in range(int(seconds / step)):
        clock.now += step
        pos += step
        await s.progress(song_id, pos)


def test_threshold():
    assert threshold(200) == 100
    assert threshold(1200) == 240
    assert threshold(0) == 240


async def test_now_playing_then_scrobble_at_half():
    s, clock, calls = make()
    s.track_loaded("a", 200)
    await s.progress("a", 0)
    assert calls == [("a", False, None)]
    await play(s, clock, "a", 0, 98)
    assert len(calls) == 1
    await play(s, clock, "a", 98, 4)
    assert calls[-1] == ("a", True, 1_000_000)
    await play(s, clock, "a", 102, 50)
    assert len(calls) == 2  # submitted once


async def test_four_minutes_cap_for_long_tracks():
    s, clock, calls = make()
    s.track_loaded("long", 3600)
    await play(s, clock, "long", 0, 242)
    assert calls[-1][1] is True


async def test_seek_forward_does_not_count():
    s, clock, calls = make()
    s.track_loaded("a", 200)
    await play(s, clock, "a", 0, 10)
    clock.now += 2
    await s.progress("a", 150)  # jumped forward
    assert s.listened == 10
    assert all(not submission for _, submission, _ in calls)


async def test_pause_gap_does_not_count():
    s, clock, _calls = make()
    s.track_loaded("a", 200)
    await play(s, clock, "a", 0, 10)
    s.stopped()
    clock.now += 600
    await s.progress("a", 10)
    assert s.listened == 10


async def test_progress_for_other_song_is_ignored():
    s, _clock, calls = make()
    s.track_loaded("a", 200)
    await s.progress("b", 0)
    assert calls == []


async def test_coordinator_reports_progress():
    h = Harness()
    calls: list[tuple[str, bool]] = []

    async def sink(song_id: str, submission: bool, _time: int | None) -> None:
        calls.append((song_id, submission))

    clock = Clock()
    h.c._scrobbler = Scrobbler(sink, clock)
    await h.c.start()
    await h.c.select_device("dev1")
    await h.c.play_songs(songs(2), 0)  # 200 s tracks
    for t in range(0, 104, 2):
        clock.now += 2
        h.target.media("PLAYING", t=float(t))
    for _ in range(10):
        await asyncio.sleep(0)
    assert calls == [("s0", False), ("s0", True)]
    for task in h.c._tasks:
        task.cancel()
