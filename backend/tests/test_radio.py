"""Track and artist radios: source fallbacks and endless refill."""

from __future__ import annotations

import asyncio

import pytest

from casthome.playback import coordinator as coordinator_module
from casthome.playback.coordinator import PlaybackError
import random

from casthome.playback.radio import make_artist_radio_builder, make_radio_builder
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
        self.counts = getattr(self, "counts", []) + [count]
        return await self._answer("similar2", self.similar2)

    async def get_top_songs(self, artist, count=50):
        return await self._answer("top", self.top)


async def test_uses_track_similarity_first_and_labels_audiomuse():
    source = FakeSource(similar=[SEED, *tracks("s", 3), tracks("s", 1)[0]])
    songs, label = await make_radio_builder(source)(SEED, {SEED.id})
    assert label == "audiomuse" and [s.id for s in songs] == ["s0", "s1", "s2"]  # seed and duplicate dropped
    assert source.calls == ["similar"]


async def test_without_sonic_extension_label_is_generic():
    _songs, label = await make_radio_builder(FakeSource(similar=tracks("s", 2), ext=()))(SEED, set())
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


async def test_radio_from_the_track_being_played_keeps_it_playing(h):
    h.c._radio_builder = make_radio_builder(FakeSource(similar=tracks("s", 10)))
    await h.c.play_songs([SEED, *tracks("x", 2)], 0, "Album")
    await h.c.add_songs([Song(id="q", title="Q")], AddMode.QUEUE)
    current_uid = h.c.queue.current.uid
    loads = len(h.target.loads)
    await h.c.start_radio(SEED)
    snap = h.c.queue_snapshot()
    # Not restarted: same entry, no new load on the device.
    assert h.c.queue.current.uid == current_uid and len(h.target.loads) == loads
    # Next in queue kept, then the radio instead of the rest of the album.
    assert [i["id"] for i in snap["items"][:3]] == ["seed", "q", "s0"]
    assert "x0" not in [i["id"] for i in snap["items"]]
    assert snap["radio"] is True and snap["context_name"] == "Seed"


async def test_radio_from_another_track_still_starts_with_it(h):
    h.c._radio_builder = make_radio_builder(FakeSource(similar=tracks("s", 10)))
    await h.c.play_songs(tracks("x", 2), 0, "Album")
    loads = len(h.target.loads)
    await h.c.start_radio(SEED)
    assert playing_id(h) == "seed" and len(h.target.loads) == loads + 1


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


# --- artist radio -------------------------------------------------------------


def by(artist_id: str, prefix: str, n: int) -> list[Song]:
    return [Song(id=f"{prefix}{i}", title=f"{prefix}{i}", artist_id=artist_id, duration=200) for i in range(n)]


async def test_artist_radio_shuffles_a_large_pool_of_the_artist_and_similar_artists():
    source = FakeSource(similar2=[*by("ar1", "a", 30), *by("ar2", "o", 30)])
    build = make_artist_radio_builder(source, count=20, rng=random.Random(1))
    songs, label = await build("ar1", "Artist", {"a0"})
    assert label == "similar_artists" and source.counts == [200]  # one call, a large pool
    assert len(songs) == 20 and "a0" not in {s.id for s in songs}
    assert [s.id for s in songs] != [s.id for s in source.similar2 if s.id != "a0"][:20]  # shuffled
    assert {s.artist_id for s in songs} == {"ar1", "ar2"}


async def test_artist_radio_keeps_the_artist_to_a_third_spread_through_the_batch():
    featuring = Song(id="f", title="f", artist="Artist feat. Guest", artist_id="guest", duration=200)
    source = FakeSource(similar2=[*by("ar1", "a", 60), featuring, *by("ar2", "o", 60)])
    songs, _ = await make_artist_radio_builder(source, count=30, rng=random.Random(2))("ar1", "Artist", set())
    own = [i for i, s in enumerate(songs) if s.artist_id == "ar1" or s.id == "f"]  # a feature counts as the artist
    assert len(songs) == 30 and len(own) == 10 and own[0] == 0
    assert all(b - a > 1 for a, b in zip(own, own[1:], strict=False))  # never two in a row


async def test_artist_radio_with_only_the_artist_left_hands_over_on_refill():
    source = FakeSource(similar2=by("ar1", "a", 5))
    build = make_artist_radio_builder(source)
    songs, label = await build("ar1", "Artist", set())  # start: better than nothing
    assert len(songs) == 5 and label == "similar_artists"
    assert await build("ar1", "Artist", {"x"}) == ([], None)  # refill: the track radio takes over


async def test_artist_radio_falls_back_to_top_songs_then_nothing():
    source = FakeSource(top=by("ar1", "t", 3), fail={"similar2"})
    songs, label = await make_artist_radio_builder(source)("ar1", "Artist", set())
    assert label == "top_songs" and len(songs) == 3
    songs, label = await make_artist_radio_builder(FakeSource())("ar1", "Artist", set())
    assert songs == [] and label is None


async def test_start_artist_radio_opens_with_the_artist_and_keeps_next_in_queue(h):
    pool = [*by("ar2", "o", 3), *by("ar1", "a", 2)]

    async def builder(artist_id, name, exclude):
        return [s for s in pool if s.id not in exclude], "similar_artists"

    h.c._artist_radio_builder = builder
    await h.c.play_songs(tracks("x", 2), 0, "Album")
    await h.c.add_songs([Song(id="q", title="Q")], AddMode.QUEUE)
    source = await h.c.start_artist_radio("ar1", "Artist")
    snap = h.c.queue_snapshot()
    assert source == "similar_artists" and playing_id(h) == "a0"  # one of the artist's own tracks first
    assert snap["radio"] is True and snap["context_name"] == "Artist"
    assert h.c.queue.radio_artist == ("ar1", "Artist")
    assert [i["id"] for i in snap["items"][:2]] == ["a0", "q"]


async def test_artist_radio_without_results_reports_it(h):
    h.c._artist_radio_builder = make_artist_radio_builder(FakeSource())
    with pytest.raises(PlaybackError) as err:
        await h.c.start_artist_radio("ar1", "Artist")
    assert err.value.code == "no_similar_tracks" and h.c.queue.radio is False


async def test_artist_radio_refills_from_the_artist_then_follows_the_last_track(h, monkeypatch):
    monkeypatch.setattr(coordinator_module, "RADIO_REFILL_AT", 2)
    artist_batches = [by("ar1", "a", 3), by("ar1", "b", 3), []]  # the third refill finds nothing new
    calls: list[str] = []

    async def artist_builder(artist_id, name, exclude):
        calls.append("artist")
        return ([s for s in artist_batches.pop(0) if s.id not in exclude], "similar_artists") if artist_batches else ([], None)

    async def track_builder(seed, exclude):
        calls.append(f"track:{seed.id}")
        return [s for s in tracks("t", 3) if s.id not in exclude], "audiomuse"

    h.c._artist_radio_builder = artist_builder
    h.c._radio_builder = track_builder

    async def advance(times: int) -> None:
        for _ in range(times):
            await h.c.next()
            for _ in range(10):
                await asyncio.sleep(0)

    await h.c.start_artist_radio("ar1", "Artist")  # a0 a1 a2
    await advance(2)  # a2 playing, nothing left -> refill from the artist
    assert [e.item.id for e in h.c.queue.entries][-3:] == ["b0", "b1", "b2"]
    assert h.c.queue.radio_artist == ("ar1", "Artist")
    await advance(3)  # b2 playing -> the artist has nothing new: follow the last track
    assert calls[-2:] == ["artist", "track:b2"]
    assert [e.item.id for e in h.c.queue.entries][-3:] == ["t0", "t1", "t2"]
    assert h.c.queue.radio_artist is None and h.c.queue.radio is True
    assert len({e.item.id for e in h.c.queue.entries}) == len(h.c.queue)  # no repeats


async def test_starting_an_album_ends_the_artist_radio(h):
    h.c._artist_radio_builder = make_artist_radio_builder(FakeSource(similar2=by("ar1", "a", 3)))
    await h.c.start_artist_radio("ar1", "Artist")
    await h.c.play_songs(tracks("x", 2), 0, "Album")
    assert h.c.queue.radio is False and h.c.queue.radio_artist is None
