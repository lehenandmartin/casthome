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


# --- similar artists (bottom of the artist page) -----------------------------

from casthome.api.library import includes_artist, pick_similar_artists  # noqa: E402


def artist(i: str, name: str, albums: int = 1) -> Artist:
    return Artist(id=i, name=name, album_count=albums)


def test_similar_artists_skip_the_artist_duos_and_empty_pages() -> None:
    madonna = artist("m", "Madonna", 19)
    library = {a.id: a for a in [madonna, artist("r", "RAYE", 4), artist("j", "Jungle", 4), artist("k", "Kylie"),
                                  artist("d", "Madonna & Charli xcx"), artist("z", "3OH!3", 0)]}
    lastfm = [library["r"], library["d"], library["z"], library["m"]]
    songs = [Song(id=f"s{i}", title="t", artist_id=a) for i, a in enumerate(["j", "m", "k", "j", "r", "d", "x"])]
    picked = pick_similar_artists(madonna, lastfm, songs, library)
    # Last.fm order first, then by presence among similar tracks; unknown ids ("x") dropped.
    assert [a.name for a in picked] == ["RAYE", "Jungle", "Kylie"]


def test_similar_artists_are_limited() -> None:
    library = {str(i): artist(str(i), f"A{i}") for i in range(30)}
    picked = pick_similar_artists(artist("me", "Me"), list(library.values()), [], library, limit=12)
    assert len(picked) == 12


def test_includes_artist_matches_whole_names_only() -> None:
    assert includes_artist("Madonna", "Britney Spears feat. Madonna")
    assert includes_artist("Charli xcx", "Madonna & Charli XCX")
    assert not includes_artist("Kesha", "Keshawn")
