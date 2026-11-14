"""Artist page extras: popular tracks (or your most played) and favorite count."""

from __future__ import annotations

from types import SimpleNamespace

from casthome.api.library import artist_highlights
from casthome.subsonic.models import Artist, Song


def song(i: int, plays: int = 0) -> Song:
    return Song(id=f"s{i}", title=f"T{i}", play_count=plays)


class FakeSubsonic:
    def __init__(self, top: list[Song]) -> None:
        self.top = top
        self.asked: list[str] = []

    async def get_artist(self, artist_id: str):  # type: ignore[no-untyped-def]
        return Artist(id=artist_id, name="Madonna"), []

    async def get_top_songs(self, artist: str, count: int = 50) -> list[Song]:
        self.asked.append(artist)
        return self.top


class FakeNative:
    def __init__(self, played: list[Song], liked: int) -> None:
        self.played, self.liked = played, liked
        self.calls: list[dict] = []

    async def get_songs(self, sort="recent", offset=0, size=100, starred=False, artist_id=None):  # type: ignore[no-untyped-def]
        self.calls.append({"sort": sort, "starred": starred, "artist_id": artist_id})
        if starred:
            return [], self.liked
        return self.played, len(self.played)


def request_for(subsonic: FakeSubsonic, native: FakeNative):  # type: ignore[no-untyped-def]
    ctx = SimpleNamespace(subsonic=subsonic, native=native)
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ctx=ctx)))


async def test_popular_tracks_come_from_top_songs() -> None:
    subsonic, native = FakeSubsonic([song(1), song(2)]), FakeNative([], liked=58)
    result = await artist_highlights("a1", request_for(subsonic, native))  # type: ignore[arg-type]
    assert result["top_source"] == "popular"
    assert [s["id"] for s in result["top"]] == ["s1", "s2"]
    assert result["liked_count"] == 58
    assert subsonic.asked == ["Madonna"]
    assert {"sort": "recent", "starred": True, "artist_id": "a1"} in native.calls


async def test_without_popularity_falls_back_to_your_most_played() -> None:
    subsonic, native = FakeSubsonic([]), FakeNative([song(3, plays=4), song(4, plays=0)], liked=0)
    result = await artist_highlights("a1", request_for(subsonic, native))  # type: ignore[arg-type]
    assert result["top_source"] == "most_played"
    assert [s["id"] for s in result["top"]] == ["s3"]  # never played: left out
