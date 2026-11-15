"""Lists the Subsonic API cannot give: Navidrome's API, or fallbacks elsewhere."""

import httpx
import respx

from casthome.subsonic.client import SubsonicClient
from casthome.subsonic.library import Library, capabilities
from casthome.subsonic.models import Album, SearchResult, Song
from casthome.subsonic.native import NativeClient

URL = "http://music"


async def _pw() -> str:
    return "pw"


def ok(server_type: str | None, **body):
    payload = {"status": "ok", "version": "1.16.1", **body}
    if server_type is not None:
        payload["type"] = server_type
    return httpx.Response(200, json={"subsonic-response": payload})


def song(i: int, **kw) -> Song:
    return Song(id=f"s{i}", title=kw.pop("title", f"T{i}"), **kw)


STARRED = SearchResult(
    artists=[],
    albums=[
        Album(id="a1", name="Zebra", created="2024-01-01T00:00:00Z", play_count=1),
        Album(id="a2", name="apple", created="2025-01-01T00:00:00Z", play_count=9),
    ],
    songs=[
        song(1, title="b", artist_id="ar1", created="2024-01-01", play_count=3),
        song(2, title="A", artist_id="ar2", created="2025-01-01", play_count=7),
        song(3, title="c", artist_id="ar1", created="2023-01-01", play_count=0),
    ],
)


def make_library(http: httpx.AsyncClient) -> tuple[Library, SubsonicClient]:
    sub = SubsonicClient(URL, "me", _pw, http)

    async def starred() -> SearchResult:
        return STARRED

    return Library(sub, NativeClient(URL, "me", _pw, http), starred), sub


def test_capabilities():
    assert capabilities(None) == {"all_tracks": True, "play_history": True}
    assert capabilities("navidrome")["all_tracks"] is True
    assert capabilities("gonic") == {"all_tracks": False, "play_history": False}
    assert capabilities("")["all_tracks"] is False  # plain Subsonic


@respx.mock
async def test_other_server_sorts_and_pages_favorites():
    respx.get(f"{URL}/rest/ping").mock(return_value=ok("gonic"))
    native = respx.get(url__startswith=f"{URL}/api/").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as http:
        lib, sub = make_library(http)
        items, total = await lib.get_songs("title", 0, 2, starred=True)
        assert [s.id for s in items] == ["s2", "s1"] and total == 3
        items, total = await lib.get_songs("recent", 0, 10, starred=True, artist_id="ar1")
        assert [s.id for s in items] == ["s1", "s3"] and total == 2
        items, _ = await lib.get_songs("frequent", 0, 1, starred=True)
        assert [s.id for s in items] == ["s2"]
        assert await lib.get_songs("recent", 0, 10) == ([], 0)  # every track: Navidrome only
        assert [a.id for a in await lib.get_albums("alphabeticalByName", 0, 10, starred=True)] == ["a2", "a1"]
        assert [a.id for a in await lib.get_albums("newest", 0, 10, starred=True)] == ["a2", "a1"]
        assert await lib.get_on_repeat(days=30, limit=5) == []
    assert sub.server_type == "gonic" and not native.called


@respx.mock
async def test_navidrome_uses_its_own_api():
    respx.get(f"{URL}/rest/ping").mock(return_value=ok("navidrome"))
    respx.post(f"{URL}/auth/login").mock(return_value=httpx.Response(200, json={"token": "jwt"}))
    route = respx.get(url__startswith=f"{URL}/api/song").mock(
        return_value=httpx.Response(200, json=[{"id": "x", "title": "X"}], headers={"x-total-count": "1"})
    )
    async with httpx.AsyncClient() as http:
        lib, _ = make_library(http)
        items, total = await lib.get_songs("recent", 0, 10)
    assert [s.id for s in items] == ["x"] and total == 1 and route.called


@respx.mock
async def test_server_type_is_read_from_any_answer_and_reported():
    respx.get(f"{URL}/rest/getGenres").mock(return_value=ok(None, genres={}))
    seen: list[str] = []
    async with httpx.AsyncClient() as http:
        sub = SubsonicClient(URL, "me", _pw, http)
        sub.on_server_type = seen.append
        await sub.get_genres()
        await sub.get_genres()
        assert sub.server_type == "" and await sub.detect_server_type() == ""
    assert seen == [""]  # reported once, without a ping
