"""Opt-in preloading of the next track on the Cast receiver queue."""

import asyncio

import pytest

from casthome.cast.types import MediaEvent
from casthome.playback import preload
from casthome.playback.coordinator import Status
from tests.test_coordinator import Harness, playing_id, songs, uid_of


@pytest.fixture
async def h():
    harness = Harness()
    harness.c.preload_enabled = True
    await harness.c.start()
    await harness.c.select_device("dev1")
    await harness.c.play_songs(songs(3), 0)  # 200 s tracks
    yield harness
    for task in harness.c._tasks:
        task.cancel()


def at(h: Harness, t: float, url: str | None = None, state: str = "PLAYING", reason: str | None = None) -> None:
    h.target.sink(MediaEvent(state, reason, url or h.target.last_url, t, 200.0))


async def test_preloads_only_near_the_end(h):
    at(h, 100)
    await h.settle()
    assert h.target.enqueued == []
    at(h, 185)
    at(h, 187)
    await h.settle()
    assert len(h.target.enqueued) == 1 and "id=s1" in h.target.enqueued[0]


async def test_follows_the_receiver_to_the_preloaded_track(h):
    at(h, 185)
    await h.settle()
    preloaded = h.target.enqueued[0]
    at(h, 200, state="IDLE", reason="FINISHED")
    at(h, 0.5, url=preloaded)
    await h.settle()
    assert playing_id(h) == "s1" and h.c.status == Status.PLAYING
    assert len(h.target.loads) == 1  # no reload: gapless


async def test_stale_preload_is_replaced(h):
    at(h, 185)
    await h.settle()
    preloaded = h.target.enqueued[0]
    await h.c.move_entry(uid_of(h, "s2"), 1)  # s2 is now next, not s1
    at(h, 0.5, url=preloaded)
    await h.settle()
    assert playing_id(h) == "s2" and "id=s2" in h.target.last_url


async def test_watchdog_loads_when_receiver_does_not_switch(h, monkeypatch):
    monkeypatch.setattr(preload, "PRELOAD_SWITCH_TIMEOUT_S", 0.01)
    at(h, 185)
    await h.settle()
    at(h, 200, state="IDLE", reason="FINISHED")
    await h.settle()
    assert len(h.target.loads) == 1
    await asyncio.sleep(0.05)
    await h.settle()
    assert playing_id(h) == "s1" and len(h.target.loads) == 2


async def test_manual_next_discards_preload(h):
    at(h, 185)
    await h.settle()
    preloaded = h.target.enqueued[0]
    await h.c.next()
    assert h.c._preload is None
    at(h, 1.0, url=preloaded)  # a late status for the discarded item
    await h.settle()
    assert playing_id(h) == "s1" and len(h.target.loads) == 2


async def test_disabled_by_default():
    harness = Harness()
    await harness.c.start()
    await harness.c.select_device("dev1")
    await harness.c.play_songs(songs(2), 0)
    at(harness, 190)
    await harness.settle()
    assert harness.target.enqueued == []
    for task in harness.c._tasks:
        task.cancel()
