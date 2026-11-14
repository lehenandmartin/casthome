import httpx
import pytest
import respx

from casthome.subsonic.client import InvalidCredentialsError
from casthome.subsonic.native import NativeClient, song_from_native

ND = "http://nd"


async def _pw() -> str:
    return "pw"


def test_song_mapping_and_cover_ids():
    with_art = song_from_native(
        {"id": "s1", "title": "T", "artist": "A", "albumId": "al1", "duration": 200.4, "trackNumber": 3,
         "suffix": "FLAC", "hasCoverArt": True, "playCount": 4, "rating": 4, "starred": True}
    )
    assert with_art.cover_art == "mf-s1" and with_art.suffix == "flac" and with_art.content_type == "audio/flac"
    assert with_art.track == 3 and with_art.user_rating == 4 and with_art.starred
    without_art = song_from_native({"id": "s2", "title": "U", "albumId": "al9", "hasCoverArt": False})
    assert without_art.cover_art == "al-al9" and without_art.starred is False


@respx.mock
async def test_get_songs_sorts_pages_and_reads_total():
    respx.post(f"{ND}/auth/login").mock(return_value=httpx.Response(200, json={"token": "jwt1"}))
    route = respx.get(url__startswith=f"{ND}/api/song").mock(
        return_value=httpx.Response(200, json=[{"id": "a", "title": "A"}], headers={"x-total-count": "3854"})
    )
    async with httpx.AsyncClient() as http:
        items, total = await NativeClient(ND, "me", _pw, http).get_songs("recent", 100, 50)
    request = route.calls.last.request
    assert request.headers["x-nd-authorization"] == "Bearer jwt1"
    q = dict(request.url.params)
    assert q["_sort"] == "createdAt" and q["_order"] == "DESC" and q["_start"] == "100" and q["_end"] == "150"
    assert total == 3854 and items[0].id == "a"


@respx.mock
async def test_expired_token_logs_in_again_once():
    login = respx.post(f"{ND}/auth/login").mock(
        side_effect=[httpx.Response(200, json={"token": "old"}), httpx.Response(200, json={"token": "new"})]
    )
    respx.get(url__startswith=f"{ND}/api/song").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json=[], headers={"x-total-count": "0"})]
    )
    async with httpx.AsyncClient() as http:
        items, total = await NativeClient(ND, "me", _pw, http).get_songs("title")
    assert login.call_count == 2 and items == [] and total == 0


@respx.mock
async def test_wrong_password():
    respx.post(f"{ND}/auth/login").mock(return_value=httpx.Response(401))
    async with httpx.AsyncClient() as http:
        with pytest.raises(InvalidCredentialsError):
            await NativeClient(ND, "me", _pw, http).get_songs()


@respx.mock
async def test_on_repeat_keeps_last_30_days_and_ranks_by_plays():
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    iso = lambda days: (now - timedelta(days=days)).isoformat().replace("+00:00", "Z")  # noqa: E731
    respx.post(f"{ND}/auth/login").mock(return_value=httpx.Response(200, json={"token": "t"}))
    rows = [
        {"id": "a", "title": "A", "playDate": iso(1), "playCount": 2},
        {"id": "b", "title": "B", "playDate": iso(3), "playCount": 9},
        {"id": "c", "title": "C", "playDate": iso(10), "playCount": 5},
        {"id": "old", "title": "Old", "playDate": iso(45), "playCount": 99},  # outside the window
    ]
    route = respx.get(url__startswith=f"{ND}/api/song").mock(return_value=httpx.Response(200, json=rows))
    async with httpx.AsyncClient() as http:
        top = await NativeClient(ND, "me", _pw, http).get_on_repeat(days=30, limit=2)
    assert [s.id for s in top] == ["b", "c"]
    assert dict(route.calls.last.request.url.params)["_sort"] == "playDate"


def test_artists_fallback_from_most_played_albums():
    from casthome.api.home import artists_from_albums
    from casthome.subsonic.models import Album

    albums = [
        Album(id="1", name="X", artist="Troye", artist_id="ar1"),
        Album(id="2", name="Y", artist="Troye", artist_id="ar1"),
        Album(id="3", name="Z", artist="Slayyyter", artist_id="ar2"),
    ]
    artists = artists_from_albums(albums, 5)
    assert [a.name for a in artists] == ["Troye", "Slayyyter"] and artists[0].cover_art == "ar-ar1"


@respx.mock
async def test_favorite_albums_use_native_sort_and_filter():
    respx.post(f"{ND}/auth/login").mock(return_value=httpx.Response(200, json={"token": "t"}))
    route = respx.get(url__startswith=f"{ND}/api/album").mock(
        return_value=httpx.Response(
            200, json=[{"id": "al1", "name": "BRAT", "albumArtist": "Charli xcx", "albumArtistId": "ar9", "songCount": 15, "maxYear": 2024, "starred": True}]
        )
    )
    async with httpx.AsyncClient() as http:
        albums = await NativeClient(ND, "me", _pw, http).get_albums("alphabeticalByName", 0, 40, starred=True)
    q = dict(route.calls.last.request.url.params)
    assert q["starred"] == "true" and q["_sort"] == "name" and q["_order"] == "ASC"
    a = albums[0]
    assert (a.name, a.artist, a.artist_id, a.cover_art, a.year, a.starred) == ("BRAT", "Charli xcx", "ar9", "al-al1", 2024, True)
