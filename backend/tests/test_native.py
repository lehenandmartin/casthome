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
