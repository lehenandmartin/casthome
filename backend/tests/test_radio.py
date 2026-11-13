"""Track radio: source fallbacks and endless refill."""

from __future__ import annotations

import asyncio

import pytest

from casthome.playback import coordinator as coordinator_module
from casthome.playback.coordinator import PlaybackError
from casthome.playback.radio import make_radio_builder
from casthome.queue.logic import AddMode
from casthome.subsonic.client import NavidromeUnavailableError, SubsonicError
from casthome.subsonic.models import Song
from tests.test_coordinator import Harness, playing_id

SEED = Song(id="seed", title="Seed", artist="Artist", artist_id="ar1", duration=200)


def tracks(prefix: str, n: int) -> list[Song]:
    return [Song(id=f"{prefix}{i}", title=f"{prefix}{i}", duration=200) for i in range(n)]


class FakeSource:
    def __init__(self, similar=None, similar2=None, top=None, ext=("sonicSimilarity",), fail=()):
        self.similar, self.similar2, self.top = similar or [], similar2 or [], top or []
        self.ext, self.fail = set(ext), set(fail)
        self.calls: list[str] = []

    async def extensions(self):
        return self.ext

    async def _answer(self, name, value):
        self.calls.append(name)
        if name in self.fail:
            raise SubsonicError(0, "agent down") if name != "net" else NavidromeUnavailableError("down")
        return value

    async def get_similar_songs(self, item_id, count=50):
        return await self._answer("similar", self.similar)

    async def get_similar_songs2(self, artist_id, count=50):
        return await self._answer("similar2", self.similar2)

    async def get_top_songs(self, artist, count=50):
        return await self._answer("top", self.top)


async def test_uses_track_similarity_first_and_labels_audiomuse():
    source = FakeSource(similar=[SEED, *tracks("s", 3), tracks("s", 1)[0]])
    songs, label = await make_radio_builder(source)(SEED, {SEED.id})
    assert label == "audiomuse" and [s.id for s in songs] == ["s0", "s1", "s2"]  # seed and duplicate dropped
    assert source.calls == ["similar"]


async def test_without_sonic_extension_label_is_generic():
    songs, label = await make_radio_builder(FakeSource(similar=tracks("s", 2), ext=()))(SEED, set())
    assert label == "similar"


async def test_falls_back_to_similar_artists_then_top_songs():
    source = FakeSource(similar=[], similar2=tracks("a", 2), fail={"similar"})
    songs, label = await make_radio_builder(source)(SEED, set())
    assert label == "similar_artists" and source.calls == ["similar", "similar2"]
    source = FakeSource(similar=[], similar2=[], top=tracks("t", 2))
    songs, label = await make_radio_builder(source)(SEED, set())
    assert label == "top_songs" and len(songs) == 2


async def test_nothing_found_returns_empty():
    songs, label = await make_radio_builder(FakeSource())(SEED, set())
    assert songs == [] and label is None


@pytest.fixture
async def h():
    harness = Harness()
    await harness.c.start()
    await harness.c.select_device("dev1")
    yield harness
    for task in harness.c._tasks:
        task.cancel()


async def test_start_radio_plays_seed_then_similar_and_keeps_queue(h):
    h.c._radio_builder = make_radio_builder(FakeSource(similar=tracks("s", 10)))
    await h.c.play_songs(tracks("x", 2), 0, "Album")
    await h.c.add_songs([Song(id="q", title="Q")], AddMode.QUEUE)
    source = await h.c.start_radio(SEED)
    snap = h.c.queue_snapshot()
    assert source == "audiomuse" and playing_id(h) == "seed" and snap["radio"] is True
    assert [i["id"] for i in snap["items"][:3]] == ["seed", "q", "s0"] and snap["context_name"] == "Seed"


async def test_radio_without_results_reports_it(h):
    h.c._radio_builder = make_radio_builder(FakeSource())
    with pytest.raises(PlaybackError) as err:
        await h.c.start_radio(SEED)
    assert err.value.code == "no_similar_tracks"


async def test_endless_radio_refills_near_the_end_without_repeats(h, monkeypatch):
    monkeypatch.setattr(coordinator_module, "RADIO_REFILL_AT", 3)
    batches = [tracks("s", 4), [*tracks("s", 2), *tracks("r", 3)]]  # second batch overlaps the first

    async def builder(seed, exclude):
        songs = [s for s in batches.pop(0) if s.id not in exclude] if batches else []
        return songs, "audiomuse"

    h.c._radio_builder = builder
    await h.c.start_radio(SEED)  # seed + s0..s3: 4 left, no refill yet
    assert len(h.c.queue) == 5
    await h.c.next()  # s0 playing, 3 left -> still above the threshold? (3 < 3 is false)
    await h.c.next()  # s1 playing, 2 left -> refill
    for _ in range(10):
        await asyncio.sleep(0)
    assert [e.item.id for e in h.c.queue.entries][-3:] == ["r0", "r1", "r2"]
    assert len({e.item.id for e in h.c.queue.entries}) == len(h.c.queue)  # no repeats


async def test_starting_an_album_ends_the_radio(h):
    h.c._radio_builder = make_radio_builder(FakeSource(similar=tracks("s", 3)))
    await h.c.start_radio(SEED)
    await h.c.play_songs(tracks("x", 2), 0, "Album")
    assert h.c.queue.radio is False and h.c.queue_snapshot()["radio_source"] is None
